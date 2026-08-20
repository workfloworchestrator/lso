# Copyright 2023-2026 GÉANT Vereniging.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The API endpoint from which Ansible playbooks can be executed."""

import json
import os
import shutil
import subprocess
import tempfile
from itertools import chain
from pathlib import Path
from typing import Annotated, Any, NoReturn
from uuid import UUID

import ansible_runner
from fastapi import APIRouter, HTTPException, status
from pydantic import AfterValidator, BaseModel, HttpUrl

from lso.config import settings
from lso.playbook import get_playbook_path, run_playbook
from lso.schema import InventoryProblem, InventoryValidationReason, SafeName

router = APIRouter()

#: LSO validates an inventory by running Ansible's own command rather than importing Ansible, so that whichever
#: Ansible version the deployer installed is the one that decides what a valid inventory is.
INVENTORY_COMMAND = "ansible-inventory"

#: Every setting here pins something that would otherwise make the command's output depend on the machine it runs
#: on. Restricting the enabled plugins to `yaml` also stops Ansible falling back to its `ini` plugin, which would
#: otherwise report a second, unrelated set of failures for the same inventory.
ANSIBLE_ENV = {
    "ANSIBLE_INVENTORY_ENABLED": "yaml",
    "ANSIBLE_DEPRECATION_WARNINGS": "False",
    "ANSIBLE_LOCALHOST_WARNING": "False",
    "ANSIBLE_INVENTORY_UNPARSED_WARNING": "False",
    "ANSIBLE_NOCOLOR": "1",
    "ANSIBLE_FORCE_COLOR": "0",
    # Ansible refuses to start unless the locale encoding is UTF-8.
    "LC_ALL": "C.UTF-8",
    "LANG": "C.UTF-8",
    "PYTHONUTF8": "1",
}


#: A rejected inventory is the client's fault only when the inventory itself is at fault. A missing
#: `ansible-inventory` command is a deployment problem and a validation timeout is a server-side limit, so those
#: map to 5xx: a 422 would tell the caller to fix a request body that may be perfectly fine.
_REJECTION_STATUS = {
    InventoryValidationReason.VALIDATOR_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    InventoryValidationReason.TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
}


def _reject(reason: InventoryValidationReason, **details: Any) -> NoReturn:
    """Raise an HTTP error carrying a structured description of why validation failed.

    Client-side problems (a malformed inventory) become a 422; server-side ones (no validator installed, or
    validation timing out) become a 503 or 504, so callers can tell a bad inventory apart from a deployment
    problem or a transient failure. The body is an `InventoryProblem` either way.
    """
    problem = InventoryProblem(reason=reason, **details)
    status_code = _REJECTION_STATUS.get(reason, status.HTTP_422_UNPROCESSABLE_CONTENT)
    raise HTTPException(status_code=status_code, detail=problem.model_dump())


def _as_group_dict(inventory: dict[str, Any] | str) -> dict[str, Any]:
    """Represent a bare host string as a group dictionary.

    An inventory may be given as a string of newline-separated hostnames. Ansible only understands that shape
    through its `ini` inventory plugin, so spelling it out here lets validation pin the `yaml` plugin and stay
    predictable. Only the copy handed to the validator is converted; what gets passed to `ansible-runner` later is
    the inventory exactly as it was submitted.
    """
    if isinstance(inventory, str):
        hosts = [line.strip() for line in inventory.splitlines() if line.strip()]
        return {"all": {"hosts": dict.fromkeys(hosts)}}

    return inventory


def _diagnostics(stderr: str, inventory_path: str) -> list[str]:
    """Flatten Ansible's output into individual lines, with the server-side temporary path removed."""
    lines = []
    for raw_line in stderr.splitlines():
        line = raw_line.replace(inventory_path, "<inventory>").strip()
        if line and line != "<<< caused by >>>":
            lines.append(line)

    return lines


def _parsed_inventory(stdout: str) -> tuple[list[str], list[str]]:
    """Report which groups and hosts Ansible understood, given the output of `ansible-inventory --list`."""
    try:
        listing = json.loads(stdout)
    except json.JSONDecodeError:
        return [], []

    # `_meta` holds the per-host variables rather than a group, so its hosts are listed under `hostvars`.
    meta_hosts = (listing.get("_meta") or {}).get("hostvars") or {}
    groups = {name: body or {} for name, body in listing.items() if name != "_meta"}
    hosts = set(meta_hosts) | set(chain.from_iterable(body.get("hosts") or [] for body in groups.values()))

    return sorted(groups), sorted(hosts)


def _inventory_validator(inventory: dict[str, Any] | str) -> dict[str, Any] | str:
    """Validate the provided inventory format.

    Hands the inventory to Ansible's own `ansible-inventory` command and reports what it made of it. The command
    runs with a pinned environment so that the outcome depends on the inventory alone, and never on the deployer's
    `ansible.cfg`, locale, or home directory.

    This checks the static inventory format that the LSO API itself supports: a JSON object in Ansible's YAML
    inventory shape, or a newline-separated host string. It deliberately does not reproduce the deployer's
    runtime Ansible configuration. What counts as a valid request body therefore stays the same on every machine,
    while playbook *execution* keeps honouring the deployer's own configuration as usual.

    Args:
        inventory (dict[str, Any] | str): The inventory to validate, can be a dictionary or a string.

    Returns:
        The submitted inventory unchanged, if no errors are found.

    Raises:
        HTTPException: Raises HTTP error 422 (unprocessable content) if the inventory can't be parsed or the
        inventory format is incorrect, 503 if the `ansible-inventory` command is not installed, or 504 if
        validation timed out. The response body is an `InventoryProblem` in each case.

    """
    if not ansible_runner.utils.isinventory(inventory):
        _reject(InventoryValidationReason.NOT_A_MAPPING)

    command = shutil.which(INVENTORY_COMMAND)
    if command is None:
        _reject(InventoryValidationReason.VALIDATOR_UNAVAILABLE)

    with tempfile.TemporaryDirectory() as workdir:
        inventory_file = Path(workdir) / "inventory"
        inventory_file.write_text(json.dumps(_as_group_dict(inventory), ensure_ascii=False))

        # An empty config file, named so Ansible accepts it, keeps the deployer's own ansible.cfg out of the
        # validation result. Pointing `HOME` at the same throwaway directory does the same for ~/.ansible.cfg.
        config_file = Path(workdir) / "ansible.cfg"
        config_file.touch()
        environment = ANSIBLE_ENV | {
            "ANSIBLE_CONFIG": str(config_file),
            "HOME": workdir,
            "PATH": os.environ.get("PATH", ""),
        }

        try:
            result = subprocess.run(  # noqa: S603
                [command, "--list", "-i", str(inventory_file)],
                env=environment,
                text=True,
                capture_output=True,
                timeout=settings.INVENTORY_VALIDATION_TIMEOUT_SEC,
                check=False,
            )
        except subprocess.TimeoutExpired:
            _reject(InventoryValidationReason.TIMEOUT)

        messages = _diagnostics(result.stderr, str(inventory_file))

    if not messages and result.returncode == 0:
        return inventory

    groups, hosts = _parsed_inventory(result.stdout)
    # Whether any host survived parsing is the signal, rather than the wording of the messages, which differs
    # between Ansible versions.
    reason = InventoryValidationReason.REJECTED_WITH_WARNINGS if hosts else InventoryValidationReason.UNPARSABLE
    _reject(reason, messages=messages, parsed_groups=groups, parsed_hosts=hosts)


def _playbook_path_validator(playbook_name: Path) -> Path:
    """Validate the provided path to an Ansible playbook.

    Returns:
        A `Path` object, if the path is valid.

    Raises:
        HTTPException: Raises HTTP 410 if the file doesn't exist.

    """
    playbook_path = get_playbook_path(playbook_name)
    if not Path.exists(playbook_path):
        msg = f"Filename '{playbook_path}' does not exist."
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=msg)

    return playbook_path


PlaybookInventory = Annotated[dict[str, Any] | str, AfterValidator(_inventory_validator)]
PlaybookName = Annotated[SafeName, AfterValidator(_playbook_path_validator)]


class PlaybookRunResponse(BaseModel):
    """`PlaybookRunResponse` domain model schema.

    Attributes:
        job_id (UUID): The UUID generated for a Playbook execution.

    """

    job_id: UUID


class PlaybookRunParams(BaseModel):
    r"""Parameters for executing an Ansible playbook.

    Attributes:
        playbook_name (PlaybookName): The filename of a playbook that's executed. It should be present inside the
            directory defined in the configuration option ``ANSIBLE_PLAYBOOKS_ROOT_DIR``.
        callback (HttpUrl, optional): The address where LSO should call back to upon completion.
        progress (HttpUrl, optional): The address where LSO should send progress updates as the playbook executes.
        progress_is_incremental (bool, optional): Whether progress updates should be incremental or not.
        inventory (PlaybookInventory): The inventory to run the playbook against. This inventory can also include any
            host vars, if needed. When including host vars, it should be a dictionary. Can be a simple string containing
            host names when no host vars are needed. In the latter case, multiple hosts should be separated with a `\n`
            newline character only.
        extra_vars (dict[str, Any]): Extra variables that should get passed to the playbook.
            This includes any required configuration objects from the workflow orchestrator, commit comments, whether
            this execution should be a dry run, a trouble ticket number, etc. Which extra vars are required solely
            depends on what inputs the playbook requires.

    !!! danger "Inventory format"
        Note the fact if the collection of all hosts is a dictionary, and not a list of strings, Ansible expects each
        host to be a key-value pair. The key is the FQDN of a host, and the value always `null`. This is not the case
        when providing the inventory as a list of strings.

    !!! note "Inventory validation"
        The submitted inventory is validated against the static inventory format described here, using Ansible's
        built-in YAML inventory plugin in a pinned environment. The machine's own `ansible.cfg` deliberately plays
        no part in it, so what the API accepts is identical on every deployment; playbook execution itself still
        honours the deployer's Ansible configuration. A malformed inventory is rejected with a 422 whose body is an
        `InventoryProblem`; a 503 or 504 means validation itself could not run (no `ansible-inventory` command, or
        it timed out) rather than that the inventory is invalid.

    ??? example
        ```JSON
        {
            "playbook_name": "hello_world.yaml",
            "callback": "https://wfo.company.cool:8080/api/resume-workflow/",
            "progress": "https://logging.awesome.yeah:8080/playbooks/",
            "progress_is_incremental": false,
            "inventory": {
                "all": {
                    "hosts": {
                        "host1.local": {
                            "foo": "bar"
                        },
                        "host2.local": {
                            "key": "value"
                        },
                        "host3.local": null
                    }
                }
            },
            "extra_vars": {
                "weather": {
                    "today": "Sunny",
                    "tomorrow": "Overcast"
                }
            }
        }
        ```

    """

    playbook_name: PlaybookName
    callback: HttpUrl | None = None
    progress: HttpUrl | None = None
    progress_is_incremental: bool = True
    inventory: PlaybookInventory
    extra_vars: dict[str, Any] = {}


@router.post("/", response_model=PlaybookRunResponse, status_code=status.HTTP_201_CREATED)
def run_playbook_endpoint(params: PlaybookRunParams) -> PlaybookRunResponse:
    """Launch an Ansible playbook to modify or deploy a subscription instance.

    The response will contain either a job ID, or error information.

    Args:
        params: Parameters for executing a playbook.

    Returns:
        Response from the Ansible runner, including a run ID.

    """
    job_id = run_playbook(
        playbook_path=params.playbook_name,
        extra_vars=params.extra_vars,
        inventory=params.inventory,
        callback=params.callback,
        progress=params.progress,
        progress_is_incremental=params.progress_is_incremental,
    )

    return PlaybookRunResponse(job_id=job_id)
