#!/bin/bash

usage() {
  echo "Usage: $0 <larp_collection_name> <playbook-name> <remote-host> (<extra-vars> ...)" 1>&2;
  exit 2
}

if [ $# -lt 2 ]; then
  echo "Illegal number of parameters"
  usage
fi

VENV_PATH=$(mktemp -d -t larp-venv-)
if [[ ! -d "$VENV_PATH" ]]; then
  echo "Unable to create temp directory for venv"
  exit 1
fi

cleanup() {
  rm -rf "$VENV_PATH"
  echo "Deleted venv in $VENV_PATH"
}

# Always delete old venv upon exit
trap cleanup EXIT

###

echo "Creating venv in $VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
pip install -r ../requirements.txt  # FIXME
pip install ansible ansible_runner

ansible-galaxy collection install "$1"
EXTRA_OPTIONS=${*:4}
ansible-playbook "$2" -i "$3", --connection=local "$EXTRA_OPTIONS"  # FIXME: remove --connection=local
