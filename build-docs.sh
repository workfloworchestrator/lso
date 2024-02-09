#!/bin/sh
set -o errexit
set -o nounset

pip install -r requirements.txt
pip install -e .

rm -r ./docs/build/*
vale --config=docs/vale/.vale.ini sync
vale --config=docs/vale/.vale.ini docs/source/*.rst lso/*.py

sphinx-build -b html docs/source docs/build
