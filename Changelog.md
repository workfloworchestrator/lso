# Changelog

All notable changes to this project will be documented in this file.
## [1.3] - 2024-02-09
Fixes to the GAP Ansible collection
## [1.2] - 2024-02-09
Pinned to the latest GAP Ansible collection version 1.0.47
## [1.1] - 2024-02-09
GEANT GAP Ansible collection is with version in galaxy requirements.
## [1.0] - 2024-01-03
The very first major release of LSO is here! :tada: A transparent API for running Ansible playbooks on a remote machine.

- Bump the API version to 1.0 to reflect breaking changes.
- Remove obsolete endpoints that were not in use anymore.
- Remove the interpretation of ansible output into JSON, making it more transparent.
- Rely on environment variables for the configuration of Ansible, instead of supplying an inline, static `ansible.cfg` file.
- Don't filter Ansible output keys, this is left up to the consumer of the API instead.
- Some small updates to linting, code formatting, and documentation.
- Improve the quickstart in the documentation.

## [0.21] - 2023-12-14
- Add a dynamic endpoint for arbitrary playbook execution at `/api/playbook`.

## [0.1] - 2023-12-06
- initial skeleton
