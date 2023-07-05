"""Default route located at the root URL /.

For now only includes a single endpoint that responds with the current version
of the API and LSO.
"""
import pkg_resources
from fastapi import APIRouter
from pydantic import BaseModel, constr

API_VERSION = "0.1"
VERSION_STRING = constr(regex=r"\d+\.\d+")

router = APIRouter()


class Version(BaseModel):
    """Simple model for returning a version number of both the API and the `goat-lso` module."""

    api: VERSION_STRING  # type: ignore
    module: VERSION_STRING  # type: ignore


@router.get("/version")
def version() -> Version:
    """Return the version numbers of the API version, and the module version.

    :return: Version object with both API and `goat-lso` versions numbers.
    """
    return Version(api=API_VERSION, module=pkg_resources.get_distribution("goat-lso").version)
