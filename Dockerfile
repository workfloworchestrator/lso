FROM python:3.11-alpine

ARG ARTIFACT_VERSION

WORKDIR /app
COPY ./ansible-galaxy-requirements.yaml ./ansible-galaxy-requirements.yaml

RUN apk add --update --no-cache gcc libc-dev libffi-dev curl vim bash openssh

# Create ansible.cfg file and set custom paths for collections and roles
RUN mkdir -p /app/gap/collections /app/gap/roles /etc/ansible && \
    printf "[defaults]\ncollections_paths = /app/gap/ansible\nroles_path = /app/gap/ansible\nhost_key_checking=false" > /etc/ansible/ansible.cfg

RUN pip install \
        --pre \
        --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple \
        goat-lso==${ARTIFACT_VERSION}
RUN ansible-galaxy install \
                   -r ansible-galaxy-requirements.yaml \
                   -p /app/gap/ansible
RUN ansible-galaxy collection install \
                   -r ansible-galaxy-requirements.yaml \
                   -p /app/gap/ansible
EXPOSE 8000
ENTRYPOINT []
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
