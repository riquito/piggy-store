#!/usr/bin/env sh
set -e
packer.io build -only piggy-store-base-image build/packer-templates/docker-alpine-piggy-store.json
packer.io build -only docker-piggy-store build/packer-templates/docker-alpine-piggy-store.json
