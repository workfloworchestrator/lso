Quick start
==================

*This is a quick setup guide for running standalone on your local machine*

Install the module
--------------------

*One of these should be what you're looking for:*

* Install the latest module snapshot

.. code-block::

    python3 -m venv my-venv-directory
    . my-venv-directory/bin/activate

    pip install --pre --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple goat-lso

* Install the source code

.. code-block::

    python3 -m venv my-venv-directory
    . my-venv-directory/bin/activate

    git clone https://gitlab.geant.org/goat/gap/lso.git
    cd lso
    pip install -e .

    # for a full dev environment
    pip install -r requirements.txt

Running the app
-------------------

* Create a settings file, see `config.json.example` for an example.
* If necessary, set the environment vairable `ANSIBLE_HOME` to a custom path.
* Run the app like this (`app.py` starts the server on port 44444):

  .. code-block:: bash

     SETTINGS_FILENAME=/absolute/path/to/config.json python -m lso.app

Examples

* Get the version

  .. code-block:: bash

     curl http://localhost:44444/api/version

* (Not available yet) List all available playbooks

  .. code-block:: bash

     curl http://localhost:44444/api/playbook

* View the docs by loading `http://localhost:44444/docs` in your browser
