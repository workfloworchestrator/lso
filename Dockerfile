FROM python:3.11

ARG ARTIFACT_VERSION

RUN pip install \
    --pre \
    --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple \
    goat-lso==${ARTIFACT_VERSION}

# NOTE: a real config must be mounted at
# /etc/lso/config.json when running the container
RUN mkdir -p /etc/lso
COPY config.json.example /etc/lso/config.json
EXPOSE 8000

ENV SETTINGS_FILENAME=/etc/lso/config.json
CMD ["uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
