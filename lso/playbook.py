"""Module that gathers common API responses and data models."""

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any

import ansible_runner
import requests
import xmltodict
from dictdiffer import diff
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import HttpUrl

from lso import config
from lso.config import DEFAULT_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def get_playbook_path(playbook_name: str) -> Path:
    """Get the path of a playbook on the local filesystem."""
    config_params = config.load()
    return Path(config_params.ansible_playbooks_root_dir) / playbook_name


def playbook_launch_success(job_id: str) -> JSONResponse:
    """Return a :class:`PlaybookLaunchResponse` for the successful start of a playbook execution.

    :return JSONResponse: A playbook launch response that's successful.
    """
    return JSONResponse(content={"job_id": job_id}, status_code=status.HTTP_201_CREATED)


def playbook_launch_error(reason: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    """Return a :class:`PlaybookLaunchResponse` for the erroneous start of a playbook execution.

    :param str reason: The reason why a request has failed.
    :param status status_code: The HTTP status code that should be associated with this request. Defaults to HTTP 400
                               "Bad request".
    :return JSONResponse: A playbook launch response that's unsuccessful.
    """
    return JSONResponse(content={"error": reason}, status_code=status_code)


def _process_json_output(runner: ansible_runner.Runner) -> list[dict[Any, Any]]:  # ignore: C901
    """Handle Ansible runner output, and filter out redundant an overly verbose messages.

    :param :class:`ansible_runner.Runner` runner: Ansible runner that has already executed a playbook.
    :return: A filtered dictionary that contains only the relevant parts of the output from executing an Ansible
             playbook.
    :rtype: list[dict[Any, Any]]
    """
    too_verbose_keys = [
        "_ansible_no_log",
        "_ansible_delegated_vars",
        "_ansible_verbose_always",
        "ansible_facts",
        "changed",
        "file",
        "invocation",
        "include",
        "include_args",
        "server_capabilities",
    ]
    json_content = runner.stdout.read()
    parsed_output = []

    for line in json_content.strip().splitlines():
        try:
            task_output = json.loads(line)
            if "res" in task_output["event_data"] and (
                int(runner.rc) != 0 or task_output["event_data"]["res"]["changed"] is True
            ):
                #  The line contains result data, and must either consist of a change, or the playbook failed, and all
                #  steps should be included, including those that didn't make changes.
                task_result = task_output["event_data"]["res"]

                #  Remove redundant ansible-related keys.
                for remove in too_verbose_keys:
                    task_result.pop(remove, None)

                #  Remove meta-steps that just copy some temporary files, and continue to the next event
                if "state" in task_result and (task_result["state"] == "directory" or task_result["state"] == "file"):
                    continue

                if "diff_lines" in task_result:
                    #  Juniper-specific
                    #  Prevent the diff from being displayed twice, and only keep the formatted version.
                    task_result.pop("diff", None)
                elif "diff" in task_result and "before" in task_result["diff"] and "after" in task_result["diff"]:
                    #  Nokia-specific
                    #  This is a chunk of Nokia config, and the actual difference must be calculated now, instead of
                    #  simply returning the before and after.
                    before_parsed = xmltodict.parse(task_result["diff"]["before"])
                    after_parsed = xmltodict.parse(task_result["diff"]["after"])
                    #  Only leave the diff in the resulting output
                    task_result["diff"] = next(iter(diff(before_parsed, after_parsed)))

                if bool(task_result):
                    #  Only add the event if there are any relevant keys left.
                    parsed_output.append({"host": task_output["event_data"]["host"]} | task_result)

            elif "ok" in task_output["event_data"]:
                #  Always include the final message that contains the playbook execution overview.
                parsed_output.append(task_output["event_data"])

        except json.JSONDecodeError:
            #  If the line can't be decoded as JSON, include it in its entirety.
            parsed_output.append({"invalid_json": line})

    return parsed_output


def _run_playbook_proc(
    job_id: str,
    playbook_path: str,
    extra_vars: dict,
    inventory: dict[str, Any] | str,
    callback: str,
) -> None:
    """Run a playbook, internal function.

    :param str job_id: Identifier of the job that's executed.
    :param str playbook_path: Ansible playbook to be executed.
    :param dict extra_vars: Extra variables passed to the Ansible playbook.
    :param str callback: Callback URL to return output to when execution is completed.
    :param dict[str, Any] | str inventory: Ansible inventory to run the playbook against.
    """
    ansible_playbook_run = ansible_runner.run(
        playbook=playbook_path,
        inventory=inventory,
        extravars=extra_vars,
        json_mode=True,
    )

    parsed_output = _process_json_output(ansible_playbook_run)

    payload = {
        "status": ansible_playbook_run.status,
        "job_id": job_id,
        "output": parsed_output,
        "return_code": int(ansible_playbook_run.rc),
    }

    request_result = requests.post(callback, json=payload, timeout=DEFAULT_REQUEST_TIMEOUT)
    if request_result.status_code != status.HTTP_201_CREATED:
        msg = f"Callback failed: {request_result.text}"
        logger.error(msg)


def run_playbook(
    playbook_path: Path,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    callback: HttpUrl,
) -> JSONResponse:
    """Run an Ansible playbook against a specified inventory.

    :param Path playbook_path: playbook to be executed.
    :param dict[str, Any] extra_vars: Any extra vars needed for the playbook to run.
    :param dict[str, Any] | str inventory: The inventory that the playbook is executed against.
    :param :class:`HttpUrl` callback: Callback URL where the playbook should send a status update when execution is
        completed. This is used for workflow-orchestrator to continue with the next step in a workflow.
    :return: Result of playbook launch, this could either be successful or unsuccessful.
    :rtype: :class:`fastapi.responses.JSONResponse`
    """
    if not Path.exists(playbook_path):
        msg = f"Filename '{playbook_path}' does not exist."
        return playbook_launch_error(reason=msg, status_code=status.HTTP_404_NOT_FOUND)

    if not ansible_runner.utils.isinventory(inventory):
        msg = "Invalid inventory provided. Should be a string, or JSON object."
        return playbook_launch_error(reason=msg, status_code=status.HTTP_400_BAD_REQUEST)

    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_playbook_proc,
        kwargs={
            "job_id": job_id,
            "playbook_path": str(playbook_path),
            "inventory": inventory,
            "extra_vars": extra_vars,
            "callback": callback,
        },
    )
    thread.start()

    return playbook_launch_success(job_id=job_id)
