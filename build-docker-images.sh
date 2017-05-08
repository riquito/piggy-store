#!/usr/bin/env sh
set -e

# build a base image only if it's missing
if [ $(docker images --format '{{.Repository}}:{{.Tag}}' | grep 'riquito/piggy-store-base-image-alpine:latest' | wc -l) -eq 0 ]; then
    packer.io build -only piggy-store-base-image build/packer-templates/docker-alpine-piggy-store.json
fi

packer.io build -only docker-piggy-store build/packer-templates/docker-alpine-piggy-store.json
