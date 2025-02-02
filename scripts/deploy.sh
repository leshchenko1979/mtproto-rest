#!/bin/bash

# Load environment variables
source .env

# Check if environment variables are set
if [ -z "$DEPLOY_HOST" ] || [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_PATH" ]; then
    echo "Error: DEPLOY_HOST, DEPLOY_USER, and DEPLOY_PATH must be set in .env"
    exit 1
fi

echo "Deploying to $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"

# Function to clean up temporary files
cleanup() {
    echo "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# Set up trap to clean up on script exit
trap cleanup EXIT

# Create a temporary tar in the temp directory
tar --exclude='.git' \
    --exclude='sessions' \
    --exclude='logs' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -czf "$TEMP_DIR/deploy.tar.gz" .

# Copy files to remote
scp "$TEMP_DIR/deploy.tar.gz" "$DEPLOY_USER@$DEPLOY_HOST:/tmp/"

# Deploy on remote
ssh "$DEPLOY_USER@$DEPLOY_HOST" "
    cd $DEPLOY_PATH && \
    tar xzf /tmp/deploy.tar.gz && \
    rm /tmp/deploy.tar.gz && \
    docker compose down && \
    docker compose up -d --build
"

echo "Deployment complete!"
