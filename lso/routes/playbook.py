"""Routes that relate to playbooks. Contains some constructs as well.
"""
import os
from typing import List, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lso import config

router = APIRouter()


class Playbook(BaseModel):
    """Model for a Playbook.

    :param name: name of a Playbook.
    :param path: location of a Playbook on local filesystem.
    :param target: target host of a Playbook.
    :param extra_vars: extra variables that get passed on to Ansible.
    """
    name: str
    path: str
    target: str
    extra_vars: Dict[str, str]


class PlaybookList(BaseModel):
    """Model for a list of Playbooks.

    :param playbooks: A list of Playbook objects.
    """
    playbooks: List[Playbook]


class PlaybookRun(BaseModel):
    """Model of a Playbook run. Used to keep track of output and successful
    execution.

    :param result_code: Return code of a Playbook that was run.
    :param result:
    """
    result_code: int
    result: None = None


@router.get('/run/{playbook_name}')
async def run_playbook(playbook_name: str) -> JSONResponse:
    """
    Method that runs a playbook. Empty for now.

    :return: A `JSONResponse` that will report on successful executing of a
    Playbook. This is reflected in the included status code of the response.
    """
    params = config.load()
    playbook_list = os.listdir(params['playbook-dir'])
    try:
        _ = playbook_list.index(playbook_name)
    except ValueError:
        return JSONResponse(
            status_code=404,
            content=f'Playbook with name {playbook_name} not found.'
        )

    # Run playbook asynchronously with run_playbook.sh

    return JSONResponse(content=PlaybookRun(result_code=1), status_code=202)
