---
icon: lucide/book
---

# Introduction

The Lightweight Service Orchestrator (LSO) is a simple tool designed to run tasks remotely. These can be Ansible
playbooks or custom scripts. Requests are made through a REST API, as a straightforward way to send instructions.
This includes Ansible inventories, variables, and other parameters, making automation easier and more flexible.

## Why LSO

LSO was built to solve a common problem: running Ansible playbooks from a remote machine without setting
up a complicated system. Many tools, like AWX, are powerful but require complex setups, like Kubernetes,
and are tied to specific ecosystems.

We wanted a lightweight, easy-to-use solution that works without extra layers. That’s why we created LSO.

## What LSO Does

LSO is a small FastAPI server that receives requests from remote services and uses `ansible-runner` to execute
playbooks. It can also execute Python scripts directly, without Ansible.

In short, LSO will:

- Accept playbook name, inventory details, and extra variables as input.
- Runs the playbook on Ansible using this information.
- Sends the results back, including the output and execution status.

When running a Python scirpt, it follows the same pattern: take input in the API call, run the script in the executor,
and return the results of the script to the user at their specified endpoint.
