# Contributing

We use [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for managing dependencies.

To get started with a development environment, clone this repository and run:

```
uv venv --python 3.13
. .venv/bin/activate
uv sync --all-extras --dev
pre-commit install
```
