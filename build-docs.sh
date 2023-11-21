#!/bin/sh
set -o errexit
set -o nounset

pip install -r requirements.txt
pip install -e .

export SETTINGS_FILENAME=./config.json.example
python docs/dump-openapi-spec.py

rm -r ./docs/build/*
vale --config=docs/vale/.vale.ini sync
vale --config=docs/vale/.vale.ini docs/source/*.rst lso/*.py
sphinx-build -b html docs/source docs/build

unset SETTINGS_FILENAME
