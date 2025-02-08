# MTProto-REST: Telegram User Account API

A secure REST API server that provides HTTPS access to Telegram user accounts via MTProto protocol. Unlike the official Telegram Bot API, this service enables programmatic control of regular user accounts through a RESTful interface, allowing message forwarding, contact search, and chat management through multiple Telegram accounts.

🔐 **Key Differentiator**: While Telegram only offers REST API for bots, MTProto-REST uniquely provides REST access to regular user accounts via MTProto protocol.

🚀 **Demo Server**: Try it out at https://mtproto-rest.redevest.ru/

## Table of Contents
- [Features](#features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#environment-setup)
- [Development](#development)
  - [Local Setup](#local-setup)
  - [Docker Development](#docker-development)
- [Deployment](#deployment)
  - [Production Deployment](#production-deployment)
  - [VS Code Integration](#vs-code-integration)
- [Architecture](#architecture)
  - [Docker Configuration](#docker-configuration)
  - [Resource Management](#resource-management)
  - [Health Monitoring](#health-monitoring)
- [API Reference](#api-reference)
  - [Health Check](#health-check)
  - [Account Management](#account-management)
  - [Message Operations](#message-operations)
  - [Search Operations](#search-operations)
- [Monitoring](#monitoring)
  - [Logging](#logging)
  - [Metrics](#metrics)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Features
- MTProto-based secure communication with Telegram servers
- Multiple Telegram account support
- Message forwarding with customizable options
- Contact and chat search functionality
- RESTful API with FastAPI
- Comprehensive logging (Logfire integration)
- Auto-generated OpenAPI documentation
- Docker and Traefik integration
- Health monitoring
- Resource management and limits

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Telegram API credentials (api_id and api_hash)
- Active Telegram account(s)
- Logfire account and API token
- Traefik reverse proxy (for production)

### Environment Setup
Create a `.env` file in the project root:

```env
# Telegram API Credentials
API_ID=your_api_id
API_HASH=your_api_hash

# Logfire Integration
LOGFIRE_TOKEN=your_logfire_token

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Deployment Configuration
DEPLOY_HOST=your_server_hostname
DEPLOY_USER=your_server_username
DEPLOY_PATH=/path/to/deployment/directory
```

## Development

### Local Setup
1. Clone the repository:
```bash
git clone https://github.com/yourusername/mtproto-rest.git
cd mtproto-rest
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python run.py
```

### Docker Development
```bash
# Start the service
docker compose up --build

# View logs
docker compose logs -f

# Stop the service
docker compose down
```

## Deployment

### Production Deployment
The project includes a deployment script:

1. Configure `.env` with deployment variables
2. Run deployment:
```bash
./scripts/deploy.sh
```

The script will:
- Package the application
- Copy to server
- Deploy via Docker Compose

### VS Code Integration
Available tasks organized by category:

**Development Tasks**
- `Local Development`: Run FastAPI server
- `Run FastAPI Server`: Direct Python execution

**Docker Tasks**
- `Docker: Start`: Build and start containers
- `Docker: Stop`: Stop and remove containers

**Deployment Tasks**
- `Deploy to Production`: Run deployment script

**SSH Tasks**
- `SSH: Connect to Production`: Open SSH connection
- `SSH: View Logs`: Show Docker logs
- `SSH: Check Status`: Display container status

To run tasks in VS Code:
1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
2. Type "Tasks: Run Task"
3. Select desired task

## Architecture

### Docker Configuration
- Base image optimization
- Python optimization level 2
- 2 Uvicorn workers
- 100 concurrent connections limit
- Optimized keep-alive settings

### Resource Management
**Limits:**
- CPU: 0.1-0.5 cores
- Memory: 128-256MB
- Log rotation: 10MB max, 3 files

**Volumes:**
- `telegram_sessions`: Session storage
- `logs`: Application logs

### Health Monitoring
- Endpoint: `/health`
- 30-second interval
- 10-second timeout
- 3 retries

## API Reference

### Health Check
```
GET /health
Response: Application health status
```

### Account Management
```
POST /api/accounts/start
POST /api/accounts/verify-code
POST /api/accounts/verify-password
GET /api/accounts/list
DELETE /api/accounts/{phone_number}
```

### Message Operations
```
POST /api/forward/messages
{
    "source_phone": "phone_number",
    "source_chat": "@channel_name",
    "destination_chat": "@channel_name",
    "message_ids": [123, 456],
    "message_links": ["https://t.me/channel_name/123"],
    "remove_sender_info": false,
    "remove_captions": false,
    "prevent_further_forwards": false,
    "silent": false
}
```

### Search Operations
```
GET /api/search/contacts
GET /api/search/chats
Query Parameters:
- phone_number
- query
- limit (default: 50)
```

## Monitoring

### Logging
Logfire integration provides:
- API endpoint metrics
- Operation tracking
- Error monitoring
- Performance analytics

### Metrics
Monitor via Logfire dashboard:
- API usage patterns
- Error rates
- Performance metrics
- Account activity
- Message statistics

## Security
- Secure credential storage
- API endpoint authentication
- Telegram ToS compliance
- Regular key rotation
- Docker security:
  - Non-root user
  - Updated base images
  - Vulnerability scanning
  - Resource limits
  - Secure volumes

## Contributing
Contributions welcome! Please submit Pull Requests.

## License
MIT License
