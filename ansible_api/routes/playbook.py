import os
from typing import List, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import ansible_runner
import venv
import tempfile

from ansible_api import config

router = APIRouter()


class Playbook(BaseModel):  # TODO: add input validation with regex
    name: str
    path: str
    target: str
    extra_vars: Dict[str, str]


class PlaybookList(BaseModel):
    playbooks: List[Playbook]


class PlaybookRun(BaseModel):
    # result: Runner | None
    result: None = None
    result_code: int


@router.get('/')
async def get_playbooks() -> PlaybookList:
    params = config.load()
    playbook_list = os.listdir(params['playbook-dir'])
    # TODO: implement
    return PlaybookList(
        playbooks=[Playbook(name=item, path='.', target='localhost', extra_vars={}) for item in playbook_list])


@router.post('/')
async def add_playbook(new_playbook: Playbook) -> Playbook:
    # TODO: implement
    # Add a new playbook available for deployment. The playbook must be available on Ansible Galaxy
    return new_playbook


@router.get('/run/{playbook_name}')
async def run_playbook(playbook_name: str) -> JSONResponse | PlaybookRun:
    # TODO: implement
    params = config.load()
    playbook_list = os.listdir(params['playbook-dir'])
    try:
        _ = playbook_list.index(playbook_name)
    except ValueError:
        return JSONResponse(status_code=404, content=f'Playbook with name {playbook_name} not found.')

    # Build a temp venv
    venv_path = tempfile.mkdtemp(prefix='workflow-', suffix='-venv')
    builder = venv.EnvBuilder(with_pip=True, system_site_packages=True)
    builder.create(venv_path)


    # Get collection from Ansible Galaxy
    # ansible_collections

    # Run playbook asynchronously
    ansible_runner.run_async()

    return PlaybookRun(result_code=1)
