# Shark Explorer - Ergo Blockchain Explorer

This project provides a modern, efficient blockchain explorer for the Ergo platform with real-time indexing, API access, and monitoring capabilities.

## Components

1. **PostgreSQL Database**: Stores indexed blockchain data
2. **Redis**: Caching layer for improved performance
3. **Shark Indexer**: Real-time blockchain data indexer
4. **Shark API**: RESTful API for querying blockchain data
5. **Prometheus**: Metrics collection
6. **Grafana**: Monitoring and visualization

## Prerequisites

- Docker and Docker Compose
- At least 100GB of free disk space
- At least 4GB of RAM

## Quick Start

1. Clone this repository:
```bash
git clone https://github.com/yourusername/shark-explorer.git
cd shark-explorer
```

2. Create a `.env` file with required configuration:
```bash
# PostgreSQL Configuration
POSTGRES_USER=shark_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=shark_explorer

# Redis Configuration
REDIS_PASSWORD=your_redis_password

# API Configuration
API_PORT=8082
LOG_LEVEL=info
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Indexer Configuration
NODE_URL=http://your.ergo.node:9053

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

3. Start the services:
```bash
docker compose -f docker-compose.prod.yml up -d
```

## Services

### API Service (port 8082)
- RESTful API for querying blockchain data
- Rate limiting and caching enabled
- Swagger documentation at `/docs`

### Grafana (port 3000)
- Access: http://localhost:3000
- Default credentials:
  - Username: admin
  - Password: (from GRAFANA_ADMIN_PASSWORD in .env)
- Pre-configured dashboards for monitoring:
  - Blockchain metrics
  - System performance
  - API statistics

### Prometheus (port 9090)
- Metrics collection and storage
- Used by Grafana for visualization

### Database Schema
The PostgreSQL database includes tables for:
- Blocks
- Transactions
- Inputs/Outputs
- Assets
- Token information
- Mining rewards
- Address statistics

## API Endpoints

See `API.md` for detailed API documentation.

## Monitoring

Access Grafana at http://localhost:3000 to view:
- Blockchain synchronization status
- System metrics
- API performance
- Error rates
- Resource usage

## Development

### Building Services
```bash
docker compose -f docker-compose.prod.yml build shark-api shark-indexer
```

### Viewing Logs
```bash
docker logs shark-explorer-shark-api-1
docker logs shark-explorer-shark-indexer-1
```

### Database Management
```bash
# Connect to PostgreSQL
docker exec -it shark-explorer-postgres-1 psql -U shark_user -d shark_explorer
```

## Troubleshooting

1. If services fail to start, check logs:
```bash
docker compose -f docker-compose.prod.yml logs
```

2. For database issues:
```bash
docker logs shark-explorer-postgres-1
```

3. To restart all services:
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request