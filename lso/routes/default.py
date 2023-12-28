"""Default route located at the root URL /.

For now only includes a single endpoint that responds with the current version of the API and LSO.
"""

from importlib import metadata

from fastapi import APIRouter
from pydantic import BaseModel, constr

API_VERSION = "1.0"
VersionString = constr(pattern=r"\d+\.\d+")

router = APIRouter()


class Version(BaseModel):
    """Simple model for returning a version number of both the API and the `goat-lso` module."""

    api: VersionString  # type: ignore[valid-type]
    module: VersionString  # type: ignore[valid-type]


@router.get("/version")
def version() -> Version:
    """Return the version numbers of the API version, and the module version.

    :return: Version object with both API and `goat-lso` versions numbers.
    """
    return Version(api=API_VERSION, module=metadata.version("goat-lso"))
