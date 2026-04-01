---
icon: lucide/package-open
---

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
uv add orchestrator-lso==3.0.0
```
