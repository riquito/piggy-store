#!/usr/bin/env sh

cd .git && git archive --format=tar.gz HEAD | docker build -t riquito/piggy-store -
