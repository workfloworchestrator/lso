FROM python:3.11

ARG ARTIFACT_VERSION

WORKDIR /app

RUN pip install \
    --pre \
    --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple \
    --target /app \
    goat-lso==${ARTIFACT_VERSION}

EXPOSE 8000
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
