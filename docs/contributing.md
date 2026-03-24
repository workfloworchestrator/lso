---
icon: lucide/handshake
---

# Contributing

We use [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for managing dependencies.

To get started with a development environment, clone this repository and run:

```sh
uv venv --python 3.12
. .venv/bin/activate
uv sync --all-extras --dev
pre-commit install
```
