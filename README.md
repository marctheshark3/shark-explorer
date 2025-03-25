# Shark Explorer - Ergo Blockchain Explorer

Shark Explorer is a modern blockchain explorer for the Ergo Platform. It provides a comprehensive set of tools to explore and analyze blockchain data, including blocks, transactions, addresses, and tokens.

## Features

- **Block Explorer**: Browse detailed information about blocks in the Ergo blockchain.
- **Transaction Viewer**: View and analyze transaction details, including inputs and outputs.
- **Address Lookup**: Check address balances, transactions history, and assets.
- **Token Analytics**: View token information, holder distribution, and related statistics.
- **Rich API**: Access blockchain data programmatically through a comprehensive API.
- **Monitoring**: Complete monitoring solution with Prometheus and Grafana dashboards.

## Architecture

Shark Explorer consists of the following components:

- **Shark Indexer**: A service that synchronizes with an Ergo node and indexes blockchain data in PostgreSQL.
- **Shark API**: A RESTful API service that provides access to indexed blockchain data.
- **PostgreSQL**: The database that stores all indexed blockchain data.
- **Redis**: Used for caching frequently accessed data.
- **Prometheus**: Used for metrics collection and monitoring.
- **Grafana**: Provides dashboards for visualizing metrics and system health.

The system follows a microservices architecture where each component can be scaled independently.

## Prerequisites

- Docker and Docker Compose
- Access to an Ergo node (local or remote)
- At least 8GB of RAM and 100GB of disk space for a full node index

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/shark-explorer.git
cd shark-explorer
```

2. Configure the environment variables:
```bash
cp .env.example .env
```
   Edit the `.env` file with your configuration settings.

3. Start the services:
```bash
docker-compose up -d
```

## API Endpoints

The API is available at `http://localhost:8080/api` by default. Here's a list of the main endpoints:

### Blocks

- `GET /blocks/latest`: Get the latest block
- `GET /blocks/{height}`: Get block at specific height
- `GET /blocks/header/{headerId}`: Get block by header ID

### Transactions

- `GET /transactions/{txId}`: Get transaction by ID
- `GET /transactions/{txId}/inputs`: Get transaction inputs
- `GET /transactions/{txId}/outputs`: Get transaction outputs

### Addresses

- `GET /addresses/{address}`: Get address information and balance
- `GET /addresses/{address}/transactions`: Get transaction history for an address
- `GET /addresses/{address}/balance`: Get address balance details

### Tokens

- `GET /tokens/{tokenId}/holders`: Get token holder distribution
- `GET /tokens/top`: Get top tokens by holder count
- `GET /tokens/address/{address}`: Get tokens owned by an address

### Info

- `GET /info/status`: Get indexer status and sync information

## Monitoring

Shark Explorer comes with a comprehensive monitoring solution using Prometheus and Grafana. Grafana dashboards are available for:

- **Indexing Progress**: Monitor the indexer's synchronization with the blockchain
- **Database Performance**: Track database metrics and performance
- **API Performance**: Monitor API usage, response times, and errors
- **Token Holders**: Analyze token distribution and holder statistics

The Grafana interface is available at `http://localhost:3000` by default.

## Transaction API Improvements

Recent improvements to the transaction API include:

- Enhanced error handling for better debugging and troubleshooting
- NULL value handling to prevent unexpected errors
- Performance optimization through proper indexing
- Improved response format with more consistent field naming

## Token Holder Analytics

The new token holder functionality allows you to:

- Track token balances by address in real-time
- View distribution of tokens across holders
- Identify top tokens by holder count
- Analyze token ownership for any address
- Monitor token issuance and movement statistics

The token holder data is automatically updated as the blockchain is indexed, with minimal performance impact on the indexing process.

## Development

### Project Structure

```
shark-explorer/
├── shark-indexer/           # Blockchain indexing service
├── shark-api/               # API service
├── db-init/                 # Database initialization scripts
├── grafana/                 # Grafana dashboards and configuration
│   └── dashboards/          # Pre-configured dashboards
├── prometheus/              # Prometheus configuration
└── tests/                   # Test scripts and utilities
```

### Running Tests

```bash
cd tests
python -m pytest
```

### Debugging

The project includes dedicated debugging tools:

```bash
python tests/transaction_debug.py --api-url http://localhost:8080/api --tx-id <transaction_id>
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Ergo Platform
- FastAPI
- PostgreSQL
- Prometheus
- Grafana