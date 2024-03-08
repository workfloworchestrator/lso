# Lightweight Service Orchestrator

LSO: an API that allows for remotely executing Ansible playbooks.

## Code documentation

Code documentation can be found at <https://workfloworchestrator.org/lso>

## Quick start

This is a quick setup guide for running on your local machine.

### As a Docker container

To run LSO as a Docker container, build an image using the `Dockerfile.example` as an example. Be sure to update
`requirements.txt` and `ansible-galaxy-requirements.yaml` accordingly, depending on your specific Ansible collection and
-role needs.

Use the Docker image to then spin up an environment. An example Docker compose file is presented below:

```yaml
  version: "3.5"
  services:
   lso:
     image: my-lso:latest
     environment:
       SETTINGS_FILENAME: /app/config.json
       ANSIBLE_ROLES_PATH: /app/lso/ansible_roles
     volumes:
       - "/home/user/config.json:/app/config.json:ro"
       - "/home/user/ansible_inventory:/opt/ansible_inventory:ro"
       - "~/.ssh/id_ed25519.pub:/root/.ssh/id_ed25519.pub:ro"
       - "~/.ssh/id_ed25519:/root/.ssh/id_ed25519:ro"
```

This will expose the API on port 8000. The container requires some more files to be mounted:

* A `config.json` that references to the location where the Ansible playbooks are stored **inside the container**.
* An Ansible inventory for all host and group variables that are used in the playbooks
* A public/private key pair for SSH authentication on external machines that are targeted by Ansible playbooks.
* Any Ansible-specific configuration (such as `collections_path`, `roles_path`, etc.) should be set using
  environment variables. `ANSIBLE_ROLES_PATH` is given as an example in the Docker compose snippet above.

### Install the module


As an alternative, below are a set of instructions for installing and running LSO directly on a machine.

*One of these should be what you're looking for:*

* Install the latest release

```bash
  python3 -m venv my-venv-directory
  . my-venv-directory/bin/activate

  pip install lso
```

* Install the source code

```bash
  git clone https://gitlab.software.geant.org/goat/gap/lso.git && cd lso
  python3 -m venv my-venv-directory
  . my-venv-directory/bin/activate
  
  pip install flit
  flit install --deps production
  
  # Or, for the full development environment
  flit install --deps develop
```

### Running the app

* Create a settings file, see `config.json.example` for an example.
* If necessary, set the environment variable `ANSIBLE_HOME` to a custom path.
* Run the app like this (`app.py` starts the server on port 44444):

```bash
  SETTINGS_FILENAME=/absolute/path/to/config.json python -m lso.app
```
