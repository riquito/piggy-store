ENV_DIR=${PWD}/.env
LOCAL_BIN=${ENV_DIR}/bin
POETRY_CACHE_DIR=$PWD/.poetry_cache_dir

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
pip install tox pytest uwsgi poetry

# This may be not necessary once we commit poetry.toml
banner "Set some poetry config, stored in poetry.toml"
poetry config --local cache-dir ${POETRY_CACHE_DIR}
poetry config --local virtualenvs.create false

banner "Ready to go, you can start with"
banner ". .env/bin/activate # enter the virtual env"
banner "poetry install # install the project dependencies"