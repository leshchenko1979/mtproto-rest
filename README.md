# Telegram REST API Server

A REST API server built with FastAPI that provides access to Telegram MTProto functionality, specifically focused on searching contacts and chats through multiple Telegram accounts.

## Features

- Search through Telegram contacts and chats
- Support for multiple Telegram accounts
- MTProto-based secure communication with Telegram servers
- RESTful API endpoints with FastAPI
- Comprehensive logging with Logfire integration
- Auto-generated OpenAPI documentation
- Containerized deployment with Docker and Traefik integration
- Health monitoring endpoints
- Resource management and limits

## Prerequisites

- Docker and Docker Compose
- Telegram API credentials (api_id and api_hash)
- Active Telegram account(s)
- Logfire account and API token
- Traefik reverse proxy setup (for production deployment)

## Environment Setup

Create a `.env` file in the project root with the following variables:

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

### Local Development
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/rest_tg.git
   cd rest_tg
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

### Direct Deployment
The project includes a deployment script that packages and deploys the application directly to your server:

1. Ensure your `.env` file is properly configured with deployment variables
2. Run the deployment script:
   ```bash
   ./scripts/deploy.sh
   ```

The script will:
- Package the application (including .env file)
- Copy it to your server
- Deploy using Docker Compose

### VS Code Tasks
The project includes several VS Code tasks organized by category:

#### Development Tasks
- `Local Development`: Default task that runs the FastAPI server
- `Run FastAPI Server`: Runs the server directly with Python

#### Docker Tasks
- `Docker: Start`: Builds and starts the Docker containers
- `Docker: Stop`: Stops and removes the Docker containers

#### Deployment Tasks
- `Deploy to Production`: Deploys the application using the deployment script
  - Note: The script will be automatically made executable when running this task

#### SSH Tasks
- `SSH: Connect to Production`: Opens an SSH connection to the production server
- `SSH: View Logs`: Shows Docker Compose logs from the production server
- `SSH: Check Status`: Displays the status of Docker containers on the production server

To use these tasks in VS Code:
1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
2. Type "Tasks: Run Task"
3. Select the desired task from the list

## Docker Configuration

### Resource Limits and Optimization
- Minimal resource usage:
  - CPU: Maximum 0.5 cores, minimum 0.1 cores
  - Memory: Maximum 256MB, minimum 128MB
- Python optimization level 2 enabled
- Worker configuration:
  - 2 Uvicorn workers
  - 100 concurrent connections limit
  - Optimized keep-alive settings
- Log rotation:
  - Maximum 10MB per file
  - 3 files rotation policy

### Volumes
The application uses Docker volumes to persist:
- `telegram_sessions`: Stores Telegram session files
- `logs`: Stores application logs

### Health Checks
- Endpoint: `/health`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

### Traefik Integration
- Automatic SSL termination
- Load balancing
- Reverse proxy configuration

## API Endpoints

### Health Check
```
GET /health
- Check the application health status
```

### Account Management
```
POST /api/accounts/start
- Add a new Telegram account (requires phone number and verification)

GET /api/accounts/list
- List all registered accounts

DELETE /api/accounts/{account_id}
- Remove an account
```

### Search Operations
```
GET /api/search/contacts
Query Parameters:
- session_id: ID of the Telegram account to use
- query: Search query string
- limit: Maximum number of results to return (default: 50)

GET /api/search/chats
Query Parameters:
- session_id: ID of the Telegram account to use
- query: Search query string
- limit: Maximum number of results to return (default: 50)
```

## Logging

The application uses Logfire's FastAPI integration for comprehensive logging:
- API endpoint access and performance metrics
- Search operations and results
- Account management events
- Error tracking and debugging information

Configure your Logfire dashboard to monitor:
- API usage patterns
- Error rates and types
- Performance metrics
- Account activity

## Security Considerations

- Store API credentials securely using environment variables
- Implement proper authentication for API endpoints
- Follow Telegram's terms of service and API usage guidelines
- Regularly rotate API keys and credentials
- Docker security best practices:
  - Use non-root user in container
  - Keep base images updated
  - Scan for vulnerabilities
  - Resource limits enforcement
  - Secure volume management

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
