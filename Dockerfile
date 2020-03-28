FROM ubuntu:20.04 as base

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-venv \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/kelseyhightower/confd/releases/download/v0.12.0-alpha3/confd-0.12.0-alpha3-linux-amd64 -O /usr/local/bin/confd ; \
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

# Create a group and user to run our app
ARG APP_USER=piggy-user
RUN groupadd -r ${APP_USER} && useradd --no-log-init -r -g ${APP_USER} ${APP_USER}

# Copy source code
COPY --chown=${APP_USER}:${APP_USER} . /app

COPY --from=base /usr/local/bin/confd /usr/local/bin/confd

# Copy pip dependencies
COPY --chown=${APP_USER}:${APP_USER} --from=base /app /app

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-distutils \
    # with non-interactive is going to be setup for UTC
    tzdata \
    uwsgi \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.env/bin:${PATH}"

USER ${APP_USER}
WORKDIR /app

ENTRYPOINT confd -confdir /app/configs -onetime -backend env && exec /usr/bin/uwsgi -i /tmp/uwsgi.ini
EXPOSE 5000