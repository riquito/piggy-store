Piggy-Store
===========

Store files easily

[![Build Status](https://api.travis-ci.com/riquito/piggy-store.svg?branch=master)](https://travis-ci.com/riquito/piggy-store)
[![Coverage Status](https://coveralls.io/repos/github/riquito/piggy-store/badge.svg?branch=master)](https://coveralls.io/github/riquito/piggy-store?branch=master)

API Documentation
-----------------

The api documentation can be [found here](https://riquito.github.io/piggy-store/)


Setup
-----

```
# Run bootstrap.sh
# It will create a local virtualenv with the necessary
# dependencies in the project folder (avoiding pollution).
./bootstrap.sh

# Enter the virtualenv
. .env/bin/activate

# Install the project dependencies
.poetry/bin/poetry install
```

Run
---

Enter the virtualenv
```
. .env/bin/activate
```

You can either use flask directly

```
python piggy-store.py
```

or run the application with uwsgi

```
uwsgi --need-app --socket 0.0.0.0:5000 --protocol=http -w piggy-store --python-autoreload=1
```

Run tests
---------

You need to run minio and redis with test configurations

```
docker-compose -f docker-compose.yml -f docker-compose.override.test.yml up s3_like user_db
```

Then just run `tox`

```
tox
```

If you want to run a single test, perhaps with more output...

```
tox -- -s tests/test_app.py::PiggyStoreTestCase --showlocals -vv
```

Try it with docker
------------------

You can try it locally using our docker image.

```
docker build -t riquito/piggy-store:latest .
```

Run the project

```
docker-compose run
```
