# Telegram REST API Server

A REST API server built with FastAPI that provides access to Telegram MTProto functionality, specifically focused on searching contacts and chats through multiple Telegram accounts.

## Features

- Search through Telegram contacts
- Search through Telegram chats with advanced filtering:
  - Date range filtering
  - Chat type filtering (private chats, groups, channels)
- Support for multiple Telegram accounts
- MTProto-based secure communication with Telegram servers
- RESTful API endpoints with FastAPI
- Comprehensive logging with Logfire integration
- Auto-generated OpenAPI documentation
- Containerized deployment with Docker

## Prerequisites

- Docker and Docker Compose
- Telegram API credentials (api_id and api_hash)
- Active Telegram account(s)
- Logfire account and API key

## Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rest_tg.git
cd rest_tg
```

2. Create a `.env` file with your configuration (see Configuration section)

3. Build and run the Docker container:
```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rest_tg.git
cd rest_tg
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your Telegram API credentials:
   - Create an application on [Telegram's developer portal](https://my.telegram.org/apps)
   - Save your `api_id` and `api_hash`

## Configuration

Create a `.env` file in the project root with the following content:
```
# Telegram API credentials
API_ID=your_api_id
API_HASH=your_api_hash

# Server configuration
HOST=0.0.0.0
PORT=8000

# Logging
LOGFIRE_API_KEY=your_logfire_api_key
```

## Usage

### Running with Docker

```bash
# Start the service
docker compose up -d

# View logs
docker compose logs -f

# Stop the service
docker compose down
```

### Running Manually

1. Start the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

2. The API will be available at `http://localhost:8000`
3. Access the interactive API documentation at `http://localhost:8000/docs`

## Docker Volume Management

The application uses Docker volumes to persist:
- Telegram session files
- Application logs
- Configuration files

Volumes are automatically created and managed by Docker Compose.

## API Endpoints

### Account Management
```
POST /api/accounts/start
- Add a new Telegram account (requires phone number and verification)

GET /api/accounts/list
- List all registered accounts

DELETE /api/accounts/{account_id}
- Remove an account
```

### Search Contacts
```
GET /api/search/contacts
Query Parameters:
- session_id: ID of the Telegram account to use
- query: Search query string
- limit: Maximum number of results to return (default: 50)
```

### Search Chats
```
GET /api/search/chats
Query Parameters:
- session_id: ID of the Telegram account to use
- query: Search query string
- chat_type: Filter by chat type (private, group, channel, all)
- start_date: Filter messages from this date (ISO format)
- end_date: Filter messages until this date (ISO format)
- limit: Maximum number of results to return (default: 50)
```

## Logging

The application uses Logfire for comprehensive logging:
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

- Store API credentials securely using Docker secrets or environment variables
- Use environment variables for sensitive data
- Implement proper authentication for API endpoints
- Follow Telegram's terms of service and API usage guidelines
- Regularly rotate API keys and credentials
- Ensure proper Docker container security practices:
  - Use non-root user in container
  - Keep base images updated
  - Scan for vulnerabilities
  - Limit container resources

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
