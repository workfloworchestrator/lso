![Lightweight Service Orchestrator](./docs/LSO_banner.jpg)
[![Supported python versions](https://img.shields.io/pypi/pyversions/orchestrator-lso.svg?color=%2334D058)](https://pypi.org/project/orchestrator-lso)
[![Downloads](https://static.pepy.tech/badge/orchestrator-lso/month)](https://pepy.tech/project/orchestrator-lso)
[![codecov](https://codecov.io/github/workfloworchestrator/lso/graph/badge.svg?token=NVFHBBU3AR)](https://codecov.io/github/workfloworchestrator/lso)

LSO: an API that allows for remotely executing Ansible playbooks.

## Quick start

This is a quick setup guide for running on your local machine.

### As a Docker container

To run LSO as a Docker container, build an image using the `Dockerfile.example` as an example. Be sure to update
`requirements.txt` and `ansible-galaxy-requirements.yaml` accordingly, depending on your specific Ansible collection and
-role needs.

Use the Docker image to then spin up an environment. An example Docker compose file is presented below:

```yaml
services:
  lso:
    image: my-lso:latest
    env_file: 
      .env  # Load default environment variables from the .env file
    volumes:
      - "/home/user/ansible_inventory:/opt/ansible_inventory:ro"
      - "~/.ssh/id_ed25519.pub:/root/.ssh/id_ed25519.pub:ro"
      - "~/.ssh/id_ed25519:/root/.ssh/id_ed25519:ro"
```

This will expose the API on port 8000. The container requires some more files to be mounted:

* An .env file: Sets default environment variables, like ANSIBLE_PLAYBOOKS_ROOT_DIR for the location of Ansible playbooks **inside the container**.
* Environment variables: Specific configurations, such as ANSIBLE_ROLES_PATH, can be directly set in the environment section. This is ideal for values you may want to override without modifying the .env file.
* An Ansible inventory for all host and group variables that are used in the playbooks
* A public/private key pair for SSH authentication on external machines that are targeted by Ansible playbooks.
* Any Ansible-specific configuration (such as `collections_path`, `roles_path`, etc.) should be set using
  environment variables. `ANSIBLE_ROLES_PATH` is given as an example in the Docker compose snippet above.

### Install the module

As an alternative, below are a set of instructions for installing and running LSO directly on a machine.

*One of these should be what you're looking for:*

* Install the latest release

```bash
  uv venv --python 3.12
  uv add orchestrator-lso
```

* Install the source code

```bash
  git clone https://github.com/workfloworchestrator/lso.git && cd lso
  uv venv --python 3.12
  . .venv/bin/activate
  
  uv sync --all-extras --dev
```

### Running the app

* Set required environment variables; see `env.example` for reference.
* If necessary, set the environment variable `ANSIBLE_HOME` to a custom path.
* Run the app like this (`app.py` starts the server on port 44444):

```bash
  source .env && python -m lso.app
```

### Task Execution Options
1. Celery (Distributed Execution)

  - For distributed task execution, set `EXECUTOR=celery`.
  - Add Celery config in your environment variables:

```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
WORKER_QUEUE_NAME=lso-worker-queue # default value is None so you don't need this by default.
```
  - Start a Celery worker:

```bash
celery -A lso.worker worker --loglevel=info -Q lso-worker-queue
```
2. ThreadPoolExecutor (Local Execution)

For local concurrent tasks, set `EXECUTOR=threadpool` and configure `MAX_THREAD_POOL_WORKERS`.

## Contributing

We use [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage dependencies.

To get started, run `uv sync`

## Code documentation

Code documentation can be found at <https://workfloworchestrator.org/lso>
