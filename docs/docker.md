# Running in Docker

It is recommended to run LSO inside a Docker container, as this helps separate installed dependencies for your Ansible
playbooks and other scripts from the rest of the host system. For this, it is not necessary to clone any repository.
However, we recommend you prepare the following files:

* `requirements.txt` - Python requirements
* `ansible-galaxy-requirements.txt` - Ansible roles and collections
* `.env.develop`, `.env.test`, etc… - Runtime variables for different environments
* `Dockerfile` - For building your image, explained below
* `compose.yaml` - For deploying your Docker image, explained below

## Building an image

To build your own Docker image, you can use the following example file:

```docker title="Dockerfile"
--8<-- "Dockerfile.example"
```

This will install:

* Any dependent system packages like `gcc` or `libc-dev`,
* the `orchestrator-lso` python package,
* further Python dependencies as defined in a `requirements.txt` file, and
* required Ansible roles and collections defined in `ansible-galaxy-requirements.yaml`.

To build the image, run something along the lines of:

```
docker build -t my-special-lso:dev .
```

More documentation for building, tagging, and publishing Docker images is available at the
[getting started](https://docs.docker.com/get-started/docker-concepts/building-images/build-tag-and-publish-an-image/)
or [Docker Build](https://docs.docker.com/build/) reference pages.

## Deploying

Using Docker Compose, your newly built Docker image can be deployed using this example snippet:

```yaml title="compose.yaml"
--8<-- "compose.yaml.example"
```

For more options, please refer to the [Docker Compose docs](https://docs.docker.com/compose/).
