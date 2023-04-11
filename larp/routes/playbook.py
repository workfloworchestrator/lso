import os
from typing import List, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from larp import config

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
async def run_playbook(playbook_name: str) -> PlaybookRun:
    # TODO: implement
    params = config.load()
    playbook_list = os.listdir(params['playbook-dir'])
    try:
        _ = playbook_list.index(playbook_name)
    except ValueError:
        return JSONResponse(status_code=404, content=f'Playbook with name {playbook_name} not found.')

    # Run playbook asynchronously with run_playbook.sh

    return PlaybookRun(result_code=1)
