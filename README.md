# Ergo Node and Indexer

This project provides a containerized setup for running an Ergo Node along with a blockchain indexer and explorer API. It allows you to have a fully functional Ergo blockchain database with search and query capabilities.

## Components

1. **Ergo Node**: The core Ergo blockchain node that syncs and validates the blockchain
2. **PostgreSQL Database**: Stores the indexed blockchain data
3. **Chain Grabber**: Indexes the blockchain by pulling data from the Ergo Node 
4. **Explorer API**: Provides a REST API to query the indexed data

## Project Structure

```
ergo-indexer/
├── docker-compose.yml           # Main configuration file
├── Dockerfile.chain-grabber     # Dockerfile for building chain grabber
├── Dockerfile.explorer-api      # Dockerfile for building explorer API
├── node-config/                 # Ergo Node configuration
│   └── ergo.conf                # Node configuration file
├── db-init/                     # Database initialization scripts
│   └── init-schema.sql          # Database schema
├── grabber-config/              # Chain Grabber configuration
│   └── application.conf         # Grabber configuration file
└── api-config/                  # Explorer API configuration
    └── application.conf         # API configuration file
```

## Prerequisites

- Docker and Docker Compose installed
- At least 100GB of free disk space (for full blockchain)
- At least 4GB of RAM

## Getting Started

1. Clone this repository:

```bash
git clone https://github.com/yourusername/ergo-indexer.git
cd ergo-indexer
```

2. Create the required directories:

```bash
mkdir -p node-config db-init grabber-config api-config
```

3. Copy the configuration files into their respective directories:

```bash
# Copy the ergo.conf file to node-config/
# Copy the init-schema.sql file to db-init/
# Copy the grabber application.conf to grabber-config/
# Copy the API application.conf to api-config/
```

4. Build the custom images for Chain Grabber and Explorer API:

```bash
docker build -f Dockerfile.chain-grabber -t ergoindexer/chain-grabber:latest .
docker build -f Dockerfile.explorer-api -t ergoindexer/explorer-api:latest .
```

5. Start the services:

```bash
docker-compose up -d
```

## Usage

Once the services are running, you can:

- Access the Ergo Node API at `http://localhost:9053`
- Access the Explorer API at `http://localhost:8080`
- Connect to the PostgreSQL database at `localhost:5432` with credentials:
  - Username: `ergo`
  - Password: `ergo_password`
  - Database: `explorer`

### Explorer API Endpoints

The Explorer API provides several endpoints to query the blockchain data:

- `/blocks` - Get information about blocks
- `/transactions` - Query transactions
- `/addresses` - Get address information and balance
- `/tokens` - Query token information
- `/stats` - Get blockchain statistics

Please refer to the [Explorer API documentation](https://github.com/ergoplatform/explorer-backend) for more details.

## Configuration

### Ergo Node Configuration

The Ergo Node is configured through `node-config/ergo.conf`. You can modify this file to adjust settings like:

- Network connections
- API settings
- Wallet settings

### Chain Grabber Configuration

The Chain Grabber is configured through `grabber-config/application.conf`. Important settings include:

- Database connection parameters
- Initial block height to start indexing from
- Processing batch size and concurrency

### Explorer API Configuration

The Explorer API is configured through `api-config/application.conf`. You can adjust:

- API server settings
- CORS settings
- Cache configuration

## Monitoring

You can monitor the containers using Docker commands:

```bash
# Check container status
docker-compose ps

# View logs for a specific service
docker-compose logs -f ergo-node
docker-compose logs -f chain-grabber
```

## Important Notes

- Initial blockchain synchronization may take several days depending on your hardware
- The Chain Grabber will start indexing once the Ergo Node has synchronized enough blocks
- Database size will grow over time as more blocks are indexed

## Troubleshooting

- If the Chain Grabber fails to start, check that the Ergo Node is properly synchronized
- If the Explorer API is not responding, ensure that the Chain Grabber has indexed some blocks
- For database connectivity issues, check the PostgreSQL logs and ensure the schema was properly initialized

## Resources

- [Ergo Platform Documentation](https://docs.ergoplatform.com/)
- [Ergo Explorer Backend Repository](https://github.com/ergoplatform/explorer-backend)
- [Ergo Node Repository](https://github.com/ergoplatform/ergo)