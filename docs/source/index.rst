Lightweight Service Orchestrator (LSO) Documentation
=====================================================

Introduction
------------

The Lightweight Service Orchestrator (LSO) is a simple tool designed to run Ansible playbooks remotely.
It provides a straightforward way to send instructions, like inventory and variables, to Ansible through
a REST API, making automation easier and more flexible.

Why LSO?
--------

LSO was built to solve a common problem: running Ansible playbooks from a remote machine without setting
up a complicated system. Many tools, like AWX, are powerful but require complex setups, like Kubernetes,
and are tied to specific ecosystems.

We wanted a lightweight, easy-to-use solution that works without extra layers. That’s why we created LSO.

What LSO Does
-------------

LSO is a small FastAPI server that receives requests from remote services and uses `ansible-runner` to execute playbooks.

It:
- Accepts the playbook name, inventory details, and extra variables as input.
- Runs the playbook on Ansible using this information.
- Sends the results back, including the output and execution status.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   modules
