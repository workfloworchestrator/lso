# Installation

Installing LSO in a virtual environment is _highly_ recommended, and there are multiple options available for this.

??? Info "Virtual Environments"

    Virtual Envirionments are highly recommended for Python packages as described in [PEP 405](https://peps.python.org/pep-0405/),
    [PEP 668](https://peps.python.org/pep-0668/), and [PEP 704](https://peps.python.org/pep-0704/). While not all of
    these standards are active, their motivations still hold. For example:

    !!! Quote "PEP 668"

        "_A long-standing practical problem for Python users has been conflicts between OS package managers and
        Python-specific package management tools like pip. These conflicts include both Python-level API
        incompatibilities and conflicts over file ownership._"

The LSO project uses `uv` for development, and it behaves similarly to `pip`.

To install LSO in your `uv` virtual environment, use:

```sh
uv init
uv add orchestrator-lso==5.0.1
```

## Installing Ansible

LSO does not install Ansible, and does not require a particular version of it. Ansible is central to what LSO does,
so it has to be present, but which version to run is your decision: your playbooks and collections dictate that, not
LSO.

LSO calls Ansible through the `ansible-playbook` and `ansible-inventory` commands and imports no Ansible code, so any
reasonably recent release works. The test suite is run against ansible-core 2.16 through to the latest release.

Install it whichever way suits your deployment, as long as the commands end up on the same `PATH` as LSO:

```sh
uv add ansible==14.2.0          # alongside LSO in the same virtual environment
pip install ansible==14.2.0     # or with pip
apt-get install ansible         # or from your distribution's packages
```

!!! warning "Ansible has to be on the `PATH` of the LSO process"

    LSO looks the commands up on the `PATH` of the process it runs in, so Ansible does not have to live in the
    same virtual environment as LSO. Installing it system-wide works, because the commands run under their own
    interpreter.

    What does break is a process whose `PATH` is narrower than your shell's. A `systemd` unit is the usual
    culprit: unless `PATH` is set in the unit file, it defaults to a minimal one that omits `/usr/local/bin` and
    any virtual environment. LSO then answers `validator_unavailable` when an inventory is submitted, even though
    Ansible runs perfectly from your shell.

Check that the LSO process, not just your shell, can find it:

```sh
ansible-playbook --version
ansible-inventory --version
```
