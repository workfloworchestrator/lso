import pkg_resources
import pydantic
from fastapi import APIRouter

API_VERSION = '0.1'
VERSION_STRING = pydantic.constr(regex=r'\d+\.\d+')

router = APIRouter()


class Version(pydantic.BaseModel):
    api: VERSION_STRING
    module: VERSION_STRING


@router.get('/version')
def version() -> Version:
    return {
        'api': API_VERSION,
        'module':
            pkg_resources.get_distribution('goat-ansible-api').version
    }
