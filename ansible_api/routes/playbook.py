import os
from typing import List, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from ansible_api import config

router = APIRouter()


class Playbook(BaseModel):  # TODO: add input validation with regex
    name: str
    path: str
    target: str
    extra_vars: Dict[str, str]


class PlaybookList(BaseModel):
    playbooks: List[Playbook]


@router.get('/')
async def get_playbooks() -> PlaybookList:
    params = config.load()
    playbook_list = os.listdir(params['playbook-dir'])
    # TODO: implement
    return PlaybookList(
        playbooks=[Playbook(name=item, path='.', target='localhost', extra_vars={}) for item in playbook_list])


@router.post('/')
async def add_playbook(new_playbook: Playbook):
    # TODO: implement
    return new_playbook
