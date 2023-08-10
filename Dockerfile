FROM python:3.11

ARG ARTIFACT_VERSION

RUN pip install \
    --pre \
    --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple \
    goat-lso==${ARTIFACT_VERSION}

CMD ["tail", "-f", "/dev/null"]
