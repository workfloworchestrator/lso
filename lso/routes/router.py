"""Routes for handling device/base_config-related requests."""

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from lso import playbook
from lso.playbook import get_playbook_path

router = APIRouter()


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
    dry_run: bool | None = True
    #: Trouble Ticket number that is associated with the deployment.
    tt_number: str
    #: The process ID generated by workflow orchestrator, used for the commit comment in the routers.
    process_id: str


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
        "commit_comment": f"GSO_PROCESS_ID: {params.process_id} - TT_NUMBER: {params.tt_number} - Deploy base config",
    }

    return playbook.run_playbook(
        playbook_path=get_playbook_path("base_config.yaml"),
        inventory=f"{params.subscription['router']['router_fqdn']}",
        extra_vars=extra_vars,
        callback=params.callback,
    )
