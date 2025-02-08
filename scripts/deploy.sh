#!/bin/bash

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Timestamp function
timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Load environment variables
source .env

# Check if environment variables are set
if [ -z "$DEPLOY_HOST" ] || [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_PATH" ]; then
    echo -e "${RED}[$(timestamp)] Error: DEPLOY_HOST, DEPLOY_USER, and DEPLOY_PATH must be set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}[$(timestamp)] Deploying to $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo -e "${YELLOW}[$(timestamp)] Created temporary directory: $TEMP_DIR${NC}"

# Function to clean up temporary files
cleanup() {
    echo -e "${YELLOW}[$(timestamp)] Cleaning up temporary files...${NC}"
    rm -rf "$TEMP_DIR"
}

# Set up trap to clean up on script exit
trap cleanup EXIT

# Create a temporary tar in the temp directory
echo -e "${YELLOW}[$(timestamp)] Creating deployment archive...${NC}"
tar --exclude='.git' \
    --exclude='sessions' \
    --exclude='logs' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -czf "$TEMP_DIR/deploy.tar.gz" .

# Copy files to remote
echo -e "${YELLOW}[$(timestamp)] Copying files to remote server...${NC}"
scp "$TEMP_DIR/deploy.tar.gz" "$DEPLOY_USER@$DEPLOY_HOST:/tmp/"

# Deploy on remote
echo -e "${YELLOW}[$(timestamp)] Deploying on remote server...${NC}"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "
    mkdir -p $DEPLOY_PATH && \
    cd $DEPLOY_PATH && \
    # Remove everything in the deployment directory
    rm -rf * .* 2>/dev/null || true && \
    tar xzf /tmp/deploy.tar.gz && \
    rm /tmp/deploy.tar.gz && \
    docker compose down && \
    docker compose up -d --build
"

echo -e "${GREEN}[$(timestamp)] Deployment complete!${NC}"
