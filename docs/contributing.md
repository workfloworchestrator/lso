# Contributing

This project uses [`uv`](https://docs.astral.sh/uv/getting-started/installation/) to manage dependencies.

To get started with a development environment, clone this repository and run:

```
uv venv --python 3.13
. .venv/bin/activate
uv sync --all-extras --dev
pre-commit install
```
