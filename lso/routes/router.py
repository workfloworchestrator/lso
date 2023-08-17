"""Routes for handling device/base_config-related requests."""
import os
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from lso import config, playbook

router = APIRouter()
config_params = config.load()


class NodeProvisioningParams(BaseModel):
    """Parameters for node provisioning.

    :param callback:
    :type callback: pydantic.HttpUrl
    :param subscription:
    :type subscription: :class:`DeviceParams`
    :param dry_run:
    :type dry_run: bool, optional
    """

    #: Callback URL that is reported back to WFO, this will allow for the workflow to continue once the playbook has
    #: been executed.
    callback: HttpUrl
    #: Parameters for the new device.
    subscription: dict
    #: Whether this playbook execution should be a dry run, or run for real. Defaults to ``True`` for obvious reasons,
    #: also making it an optional parameter.
    dry_run: Optional[bool] = True


@router.post("/")
async def provision_node(params: NodeProvisioningParams) -> playbook.PlaybookLaunchResponse:
    """Launch a playbook to provision a new node. The response will contain either a job id or error information.

    :param params: Parameters for provisioning a new node
    :type params: :class:`NodeProvisioningParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        "wfo_router_json": params.subscription,
        "dry_run": str(params.dry_run),
        "verb": "deploy",
        "commit_comment": "Base config deployed with WFO/LSO & Ansible",
    }

    playbook_path = os.path.join(config_params.ansible_playbooks_root_dir, "base_config.yaml")

    return playbook.run_playbook(
        playbook_path=playbook_path,
        inventory=f"{params.subscription['router']['router_fqdn']}",
        extra_vars=extra_vars,
        callback=params.callback,
    )