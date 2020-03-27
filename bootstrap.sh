#!/bin/bash

set -euo pipefail

ENV_DIR=${PWD}/.env
LOCAL_BIN=${ENV_DIR}/bin
POETRY_CACHE_DIR=$PWD/.poetry_cache_dir

export TERM=${TERM:-xterm}

OPT_NO_UWSGI=0
if [[ "$1" == "--no-uwsgi" ]]; then
    OPT_NO_UWSGI=1
fi

optional_uwsgi=''
if [[ OPT_NO_UWSGI -eq 0 ]] && [[ ! -x $(command -v uwsgi) ]]; then
    optional_uwsgi=uwsgi
fi

banner() {
    echo $(tput bold)$(tput setaf 2)$*$(tput sgr0)
}

# Create a local virtual environment
banner "Creating new virtualenv in ${ENV_DIR}"
python3 -m venv ${ENV_DIR}

export PATH=${LOCAL_BIN}:${PATH}

# Disable keyring, just in case. See https://github.com/pypa/pip/issues/7883
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring

# Upgrade pip, otherwise it will emit a warning.
banner "Upgrading pip in the virtual environment"
pip install --upgrade pip

# Install tools that we want to run from cli
banner "Installing necessary tools in the virtual environment"
pip install wheel tox pytest poetry ${optional_uwsgi}

banner "Ready to go, you can start with"
banner ". .env/bin/activate # enter the virtual env"
banner "poetry install # install the project dependencies"