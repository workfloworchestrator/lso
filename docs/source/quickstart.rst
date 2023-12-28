Quick start
===========

This is a quick setup guide for running standalone on your local machine.

As a Docker container
---------------------
To run LSO as a Docker container, build an image using the ``Dockerfile`` as an example. Be sure to update
``ansible-galaxy-requirements.yaml`` accordingly, depending on your specific Ansible collection and -role needs.

An example Docker compose file is presented below:

.. code-block:: yaml

   version: "3.5"
   services:
     lso:
       image: goat-lso:$LSO_VERSION_TAG
       environment:
         SETTINGS_FILENAME: /app/config.json
       volumes:
         - "/home/user/config.json:/app/config.json:ro"
         - "/home/user/ansible_inventory:/opt/ansible_inventory:ro"
         - "~/.ssh/id_ed25519.pub:/root/.ssh/id_rsa.pub:ro"
         - "~/.ssh/id_ed25519:/root/.ssh/id_rsa:ro"
       restart: unless-stopped

This will expose the API on port 8080. The container requires some more files to be mounted:

* A ``config.json`` that references to the location where the Ansible playbooks are stored **inside the container**.
* An Ansible inventory for all host and group variables that are used in the playbooks
* A public/private key pair for SSH authentication on external machines that are targeted by Ansible playbooks.

Install the module
------------------

As an alternative, below are a set of instructions for installing and running LSO directly on a machine.

*One of these should be what you're looking for:*

* Install the latest module snapshot

.. code-block:: bash

    python3 -m venv my-venv-directory
    . my-venv-directory/bin/activate

    pip install --pre --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple goat-lso

* Install the source code

.. code-block:: bash

    python3 -m venv my-venv-directory
    . my-venv-directory/bin/activate

    git clone https://gitlab.software.geant.org/goat/gap/lso.git
    cd lso
    pip install -e .

    # for a full dev environment
    pip install -r requirements.txt

Running the app
---------------

* Create a settings file, see ``config.json.example`` for an example.
* If necessary, set the environment variable ``ANSIBLE_HOME`` to a custom path.
* Run the app like this (``app.py`` starts the server on port 44444):

  .. code-block:: bash

     SETTINGS_FILENAME=/absolute/path/to/config.json python -m lso.app

Examples

* Get the version

  .. code-block:: bash

     curl http://localhost:44444/api/version

* View the docs by loading http://localhost:44444/docs in your browser
