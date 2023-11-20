FROM python:3.11

ARG ARTIFACT_VERSION

WORKDIR /app

RUN apt update && apt install -y gcc libc-dev libffi-dev curl vim && \
    addgroup -S appgroup && adduser -S appuser -G appgroup -h /app

RUN pip install \
    --pre \
    --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple \
    --target /app \
    goat-lso==${ARTIFACT_VERSION}

RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8000
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
