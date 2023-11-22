FROM python:3.11-alpine

ARG ARTIFACT_VERSION

WORKDIR /app

RUN apk add --update --no-cache gcc libc-dev libffi-dev curl vim bash openssh
    


# Create ansible.cfg file and set custom paths for collections and roles
RUN mkdir -p /app/gap/collections /app/gap/roles /etc/ansible && \
    printf "[defaults]\ncollections_paths = /app/gap/collections\nroles_path = /app/gap/roles" > /etc/ansible/ansible.cfg

RUN pip install \
    --pre \
    --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple \
    --target /app \
    goat-lso==${ARTIFACT_VERSION} && \
    pip install ansible && \
    ansible-galaxy collection install  \
                   community.general  \
                   juniper.device \
                   junipernetworks.junos \
                   geant.gap_ansible -p /app/gap/collections && \
    ansible-galaxy role install Juniper.junos -p /app/gap/roles


EXPOSE 8000
ENTRYPOINT []
CMD ["python", "-m",  "uvicorn", "lso.app:app", "--host", "0.0.0.0", "--port", "8000"]
