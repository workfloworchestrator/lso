# Copyright 2023-2025 GÉANT Vereniging.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    """Simple model for returning a version number of both the API and the `lso` module."""

    api: VersionString  # type: ignore[valid-type]
    module: VersionString  # type: ignore[valid-type]


@router.get("/version")
def version() -> Version:
    """Return the version numbers of the API version, and the module version.

    :return: Version object with both API and `lso` versions numbers.
    """
    return Version(api=API_VERSION, module=metadata.version("orchestrator-lso"))
