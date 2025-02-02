#!/bin/bash

# Create deployment directory
sudo mkdir -p /opt/rest_tg
sudo chown $USER:$USER /opt/rest_tg

# Clone the repository
git clone https://github.com/leshchenko1979/rest_tg.git /opt/rest_tg

# Create docker network if it doesn't exist
docker network create traefik-public || true

# Copy environment file
cp .env.example /opt/rest_tg/.env

# Initial deployment
cd /opt/rest_tg
docker compose up -d --build
