FROM ubuntu:20.04 as base

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-venv \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/kelseyhightower/confd/releases/download/v0.16.0/confd-0.16.0-linux-amd64 -O /usr/local/bin/confd ; \
    chmod +x /usr/local/bin/confd

WORKDIR /app

COPY bootstrap.sh .
COPY pyproject.toml .
COPY poetry.lock .

RUN /bin/bash -c '\
    ./bootstrap.sh --no-uwsgi \
    && rm bootstrap.sh  \
    && source .env/bin/activate \
    && poetry install \
'


FROM ubuntu:20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-distutils \
    # with non-interactive is going to be setup for UTC
    tzdata \
    uwsgi \
    uwsgi-plugin-python3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=base /usr/local/bin/confd /usr/local/bin/confd

# Create a group and user to run our app
RUN groupadd -r piggy-user && useradd --no-log-init -r -g piggy-user piggy-user

# Copy source code
COPY --chown=piggy-user:piggy-user . /app

# Copy pip dependencies
COPY --chown=piggy-user:piggy-user --from=base /app /app

ENV PATH="/app/.env/bin:${PATH}"
ENV VIRTUAL_ENV="/app/.env"

USER piggy-user
WORKDIR /app

ENTRYPOINT { test "$FLY_REDIS_CACHE_URL" && export APP_REDIS_HOST="${FLY_REDIS_CACHE_URL}" || true; } && confd -confdir /app/configs -onetime -backend env && exec /usr/bin/uwsgi -i /tmp/uwsgi.ini
EXPOSE 5000