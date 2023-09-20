"""Routes for handling events related to the IP trunk service."""
from os import path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from lso import config
from lso.playbook import PlaybookLaunchResponse, run_playbook

router = APIRouter()
config_params = config.load()


class IPTrunkParams(BaseModel):
    """Default parameters for an IPtrunk deployment."""

    #: The address where LSO should call back to upon completion.
    callback: HttpUrl
    #: A dictionary representation of the IP trunk subscription that is to be provisioned.
    subscription: dict
    tt_number: str
    process_id: str


class IPTrunkProvisioningParams(IPTrunkParams):
    """Additional parameters for provisioning an IPtrunk."""

    #: Whether this playbook execution should be a dry run, or run for real. Defaults to ``True`` for obvious reasons,
    #: also making it an optional parameter.
    dry_run: Optional[bool] = True
    #: The type of object that is changed.
    object: str


class IPTrunkModifyParams(IPTrunkParams):
    """Additional parameters for modifying an IPtrunk."""

    #: Whether this playbook execution should be a dry run, or run for real. Defaults to ``True`` for obvious reasons,
    #: also making it an optional parameter.
    dry_run: Optional[bool] = True
    #: The old subscription object, represented as a dictionary. This allows
    #: for calculating the difference in subscriptions.
    old_subscription: dict


class IPTrunkMigrationParams(IPTrunkParams):
    """Additional parameters for migrating an IPTrunk."""

    #: Whether this playbook execution should be a dry run, or run for real. Defaults to ``True`` for obvious reasons,
    #: also making it an optional parameter.
    dry_run: Optional[bool] = True
    #: The new Router that this IP Trunk is migrating to.
    new_side: dict
    #: An Ansible playbook verb that is passed along for indicating the phase of the migration that is performed.
    verb: str
    config_object: str


class IPTrunkCheckParams(IPTrunkParams):
    """Additional parameters for checking an IPtrunk."""

    #: The name of the check that is to be performed.
    check_name: str


class IPTrunkDeleteParams(IPTrunkParams):
    """Additional parameters for deleting an IPtrunk."""

    #: Whether this playbook execution should be a dry run, or run for real. Defaults to ``True`` for obvious reasons,
    #: also making it an optional parameter.
    dry_run: Optional[bool] = True


@router.post("/")
def provision_ip_trunk(params: IPTrunkProvisioningParams) -> PlaybookLaunchResponse:
    """Launch a playbook to provision a new IP trunk service.

    The response will contain either a job ID, or error information.

    :param params: The parameters that define the new subscription object that
        is to be deployed.
    :type params: :class:`IPTrunkProvisioningParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        "wfo_trunk_json": params.subscription,
        "dry_run": str(params.dry_run),
        "verb": "deploy",
        "config_object": params.object,
        "commit_comment": f"GSO_PROCESS_ID: {params.process_id} "
        f"- TT_NUMBER: {params.tt_number}"
        f"- Deploy config for {params.subscription['iptrunk']['geant_s_sid']} ",
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir, "iptrunks.yaml"),
        inventory=str(
            params.subscription["iptrunk"]["iptrunk_sides"][0]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
            + params.subscription["iptrunk"]["iptrunk_sides"][1]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
        ),
        extra_vars=extra_vars,
        callback=params.callback,
    )


@router.put("/")
def modify_ip_trunk(params: IPTrunkModifyParams) -> PlaybookLaunchResponse:
    """Launch a playbook that modifies an existing IP trunk service.

    :param params: The parameters that define the change in configuration.
    :type params: :class:`IPTrunkModifyParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        "wfo_trunk_json": params.subscription,
        "old_wfo_trunk_json": params.old_subscription,
        "dry_run": str(params.dry_run),
        "verb": "modify",
        "commit_comment": f"GSO_PROCESS_ID: {params.process_id} "
        f"- TT_NUMBER: {params.tt_number}"
        f"- Modify config  for {params.subscription['iptrunk']['geant_s_sid']} ",
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir, "iptrunks.yaml"),
        inventory=str(
            params.subscription["iptrunk"]["iptrunk_sides"][0]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
            + params.subscription["iptrunk"]["iptrunk_sides"][1]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
        ),
        extra_vars=extra_vars,
        callback=params.callback,
    )


@router.delete("/")
def delete_ip_trunk(params: IPTrunkDeleteParams) -> PlaybookLaunchResponse:
    """Launch a playbook that deletes an existing IP trunk service.

    :param params: Parameters that define the subscription that should get
        terminated.
    :type params: :class:`IPTrunkDeleteParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        "wfo_trunk_json": params.subscription,
        "dry_run": str(params.dry_run),
        "verb": "terminate",
        "config_object": "trunk_deprovision",
        "commit_comment": f"GSO_PROCESS_ID: {params.process_id} "
        f"- TT_NUMBER: {params.tt_number}"
        f"- Remove config for {params.subscription['iptrunk']['geant_s_sid']} ",
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir, "iptrunks.yaml"),
        inventory=str(
            params.subscription["iptrunk"]["iptrunk_sides"][0]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
            + params.subscription["iptrunk"]["iptrunk_sides"][1]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
        ),
        extra_vars=extra_vars,
        callback=params.callback,
    )


@router.post("/perform_check")
def check_ip_trunk(params: IPTrunkCheckParams) -> PlaybookLaunchResponse:
    """Launch a playbook that performs a check on an IP trunk service instance.

    :param params: Parameters that define the check that is going to be
        executed, including on which relevant subscription.
    :type params: :class:`IPTrunkCheckParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {"wfo_ip_trunk_json": params.subscription, "check": params.check_name}
    # FIXME: needs to be updated when checks become available, this includes
    # writing tests.

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir, "iptrunks_checks.yaml"),
        inventory=params.subscription["iptrunk"]["iptrunk_sides"][0]["iptrunk_side_node"]["router_fqdn"],
        extra_vars=extra_vars,
        callback=params.callback,
    )


@router.post("/migrate")
def migrate_ip_trunk(params: IPTrunkMigrationParams) -> PlaybookLaunchResponse:
    """Launch a playbook to provision a new IP trunk service.

    The response will contain either a job ID, or error information.

    :param params: The parameters that define the new subscription object that is to be migrated.
    :type params: :class:`IPTrunkMigrationParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        "wfo_trunk_json": params.subscription,
        "new_node": params.new_side["new_node"],
        "new_lag_interface": params.new_side["new_lag_interface"],
        "new_lag_member_interfaces": params.new_side["new_lag_member_interfaces"],
        "replace_index": params.new_side["replace_index"],
        "verb": params.verb,
        "config_object": params.config_object,
        "dry_run": str(params.dry_run),
        "commit_comment": f"GSO_PROCESS_ID: {params.process_id} "
        f"- TT_NUMBER: {params.tt_number}"
        f"- Deploy config for {params.subscription['iptrunk']['geant_s_sid']} ",
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir, "iptrunks_migration.yaml"),
        inventory=str(
            params.subscription["iptrunk"]["iptrunk_sides"][0]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
            + params.subscription["iptrunk"]["iptrunk_sides"][1]["iptrunk_side_node"]["router_fqdn"]
            + "\n"
            + params.new_side["new_node"]["router"]["router_fqdn"]
            + "\n"
        ),
        extra_vars=extra_vars,
        callback=params.callback,
    )
