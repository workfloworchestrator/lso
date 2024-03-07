FROM python:3.11-alpine

ARG ARTIFACT_VERSION

WORKDIR /app

RUN pip install --pre lso==${ARTIFACT_VERSION}

EXPOSE 8000
ENTRYPOINT []
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
