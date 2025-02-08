#!/bin/bash

# Create deployment directory
sudo mkdir -p /opt/mtproto-rest
sudo chown $USER:$USER /opt/mtproto-rest

# Clone the repository
git clone https://github.com/leshchenko1979/mtproto-rest.git /opt/mtproto-rest

# Create docker network if it doesn't exist
docker network create traefik-public || true

# Copy environment file
cp .env.example /opt/mtproto-rest/.env

# Initial deployment
cd /opt/mtproto-rest
docker compose up -d --build
