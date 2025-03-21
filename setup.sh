#!/bin/bash

# Ergo Node and Indexer Setup Script
# This script automates the setup of the Ergo Node and Indexer

set -e

echo "Setting up Ergo Node and Indexer..."

# Create required directories
mkdir -p node-config db-init grabber-config api-config

# Copy configuration files
echo "Copying configuration files..."
cat > node-config/ergo.conf << 'EOF'
ergo {
  # Node settings
  node {
    # Blockchain and transaction synchronization settings
    mining = false
    
    # Network settings
    stateType = "utxo"
    verifyTransactions = true
    
    # Wallet settings - disable if you don't need it
    wallet {
      seedStrengthBits = 160
    }
    
    # REST API settings
    appVersion = "4.0.16"
    keepVersions = 0
  }
  
  # API settings - enabling public API
  scorex {
    restApi {
      # API is only accessible from localhost by default
      # Set to "0.0.0.0" to allow external connections
      bindAddress = "0.0.0.0:9053"
      
      # Basic security settings
      apiKeyHash = "324dcf027dd4a30a932c441f365a25e86b173defa4b8e58948253471b81b72cf"
      
      # Cors settings
      corsAllowedOrigin = "*"
    }
    
    # P2P Network settings
    network {
      bindAddress = "0.0.0.0:9030"
      magicBytes = [1, 0, 2, 4]
      nodeName = "docker-ergo-node"
      knownPeers = [
        "213.239.193.208:9030",
        "159.65.11.55:9030",
        "165.227.26.175:9030",
        "159.89.116.15:9030",
        "136.244.110.145:9030",
        "94.130.108.35:9030"
      ]
    }
  }
}
EOF

# Create database initialization script
cat > db-init/init-schema.sql << 'EOF'
-- Create tables and indexes for the Ergo Explorer database
-- This schema is based on the explorer-backend project's schema

-- Blocks table
CREATE TABLE IF NOT EXISTS blocks (
  id VARCHAR(64) NOT NULL PRIMARY KEY,
  header_id VARCHAR(64) NOT NULL,
  parent_id VARCHAR(64) NOT NULL,
  height INTEGER NOT NULL,
  timestamp BIGINT NOT NULL,
  difficulty BIGINT NOT NULL,
  block_size INTEGER NOT NULL,
  block_coins BIGINT NOT NULL,
  block_mining_time BIGINT,
  txs_count INTEGER NOT NULL,
  txs_size INTEGER NOT NULL,
  miner_address VARCHAR(64),
  miner_name VARCHAR(128),
  main_chain BOOLEAN NOT NULL,
  version INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS blocks_height_idx ON blocks (height);
CREATE INDEX IF NOT EXISTS blocks_timestamp_idx ON blocks (timestamp);
CREATE INDEX IF NOT EXISTS blocks_parent_id_idx ON blocks (parent_id);
CREATE INDEX IF NOT EXISTS blocks_main_chain_idx ON blocks (main_chain);

-- Headers table
CREATE TABLE IF NOT EXISTS headers (
  id VARCHAR(64) NOT NULL PRIMARY KEY,
  parent_id VARCHAR(64) NOT NULL,
  version INTEGER NOT NULL,
  height INTEGER NOT NULL,
  n_bits BIGINT NOT NULL,
  difficulty BIGINT NOT NULL,
  timestamp BIGINT NOT NULL,
  state_root VARCHAR(66) NOT NULL,
  ad_proofs_root VARCHAR(64) NOT NULL,
  transactions_root VARCHAR(64) NOT NULL,
  extension_hash VARCHAR(64) NOT NULL,
  equihash_solutions VARCHAR(256) NOT NULL,
  interlinks VARCHAR[] NOT NULL,
  main_chain BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS headers_parent_id_idx ON headers (parent_id);
CREATE INDEX IF NOT EXISTS headers_height_idx ON headers (height);
CREATE INDEX IF NOT EXISTS headers_timestamp_idx ON headers (timestamp);
CREATE INDEX IF NOT EXISTS headers_main_chain_idx ON headers (main_chain);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
  id VARCHAR(64) NOT NULL PRIMARY KEY,
  block_id VARCHAR(64) NOT NULL,
  header_id VARCHAR(64) NOT NULL,
  inclusion_height INTEGER NOT NULL,
  timestamp BIGINT NOT NULL,
  index INTEGER NOT NULL,
  main_chain BOOLEAN NOT NULL,
  size INTEGER NOT NULL,
  CONSTRAINT fk_transactions_block_id FOREIGN KEY (block_id) REFERENCES blocks (id)
);

CREATE INDEX IF NOT EXISTS transactions_timestamp_idx ON transactions (timestamp);
CREATE INDEX IF NOT EXISTS transactions_inclusion_height_idx ON transactions (inclusion_height);
CREATE INDEX IF NOT EXISTS transactions_block_id_idx ON transactions (block_id);
CREATE INDEX IF NOT EXISTS transactions_header_id_idx ON transactions (header_id);
CREATE INDEX IF NOT EXISTS transactions_main_chain_idx ON transactions (main_chain);

-- Inputs table
CREATE TABLE IF NOT EXISTS inputs (
  box_id VARCHAR(64) NOT NULL,
  tx_id VARCHAR(64) NOT NULL,
  header_id VARCHAR(64) NOT NULL,
  proof_bytes VARCHAR,
  extension JSON,
  index INTEGER NOT NULL,
  main_chain BOOLEAN NOT NULL,
  address VARCHAR(64),
  CONSTRAINT pk_inputs PRIMARY KEY (box_id, tx_id),
  CONSTRAINT fk_inputs_tx_id FOREIGN KEY (tx_id) REFERENCES transactions (id)
);

CREATE INDEX IF NOT EXISTS inputs_tx_id_idx ON inputs (tx_id);
CREATE INDEX IF NOT EXISTS inputs_header_id_idx ON inputs (header_id);
CREATE INDEX IF NOT EXISTS inputs_box_id_idx ON inputs (box_id);
CREATE INDEX IF NOT EXISTS inputs_address_idx ON inputs (address);
CREATE INDEX IF NOT EXISTS inputs_main_chain_idx ON inputs (main_chain);

-- Outputs table
CREATE TABLE IF NOT EXISTS outputs (
  box_id VARCHAR(64) NOT NULL,
  tx_id VARCHAR(64) NOT NULL,
  header_id VARCHAR(64) NOT NULL,
  value BIGINT NOT NULL,
  creation_height INTEGER NOT NULL,
  index INTEGER NOT NULL,
  ergo_tree VARCHAR NOT NULL,
  address VARCHAR(64),
  additional_registers JSON,
  timestamp BIGINT NOT NULL,
  main_chain BOOLEAN NOT NULL,
  spent BOOLEAN NOT NULL,
  CONSTRAINT pk_outputs PRIMARY KEY (box_id),
  CONSTRAINT fk_outputs_tx_id FOREIGN KEY (tx_id) REFERENCES transactions (id)
);

CREATE INDEX IF NOT EXISTS outputs_tx_id_idx ON outputs (tx_id);
CREATE INDEX IF NOT EXISTS outputs_header_id_idx ON outputs (header_id);
CREATE INDEX IF NOT EXISTS outputs_address_idx ON outputs (address);
CREATE INDEX IF NOT EXISTS outputs_ergo_tree_idx ON outputs (ergo_tree);
CREATE INDEX IF NOT EXISTS outputs_timestamp_idx ON outputs (timestamp);
CREATE INDEX IF NOT EXISTS outputs_main_chain_idx ON outputs (main_chain);
CREATE INDEX IF NOT EXISTS outputs_spent_idx ON outputs (spent);

-- Assets table
CREATE TABLE IF NOT EXISTS assets (
  token_id VARCHAR(64) NOT NULL,
  box_id VARCHAR(64) NOT NULL,
  header_id VARCHAR(64) NOT NULL,
  index INTEGER NOT NULL,
  value BIGINT NOT NULL,
  name VARCHAR(128),
  decimals INTEGER,
  type VARCHAR(8),
  main_chain BOOLEAN NOT NULL,
  CONSTRAINT pk_assets PRIMARY KEY (token_id, box_id),
  CONSTRAINT fk_assets_box_id FOREIGN KEY (box_id) REFERENCES outputs (box_id)
);

CREATE INDEX IF NOT EXISTS assets_token_id_idx ON assets (token_id);
CREATE INDEX IF NOT EXISTS assets_box_id_idx ON assets (box_id);
CREATE INDEX IF NOT EXISTS assets_header_id_idx ON assets (header_id);
CREATE INDEX IF NOT EXISTS assets_main_chain_idx ON assets (main_chain);
EOF

# Create Chain Grabber configuration
cat > grabber-config/application.conf << 'EOF'
chain-grabber {
  postgres {
    url = "jdbc:postgresql://postgres:5432/explorer"
    user = "ergo"
    password = "ergo_password"
    schema = "public"
    
    # Connection pool settings
    hikari {
      maximumPoolSize = 10
      connectionTimeout = 30000
    }
  }
  
  protocol {
    network-prefix = 16
  }
  
  node {
    # Ergo node REST API endpoints
    url = "http://ergo-node:9053"
    
    # Authentication for node API
    auth {
      # Set this to your API key if you've secured your node
      api-key = ""
    }
  }
  
  # The initial height to start grabbing blocks from
  initial-height = 0
  
  # Processing settings
  batch-size = 100
  max-concurrency = 4
  
  # Whether to validate transaction data while grabbing
  validation {
    enabled = true
  }
}

akka {
  http {
    client {
      connecting-timeout = 2s
      idle-timeout = 10s
    }
  }
  
  loglevel = "INFO"
  loggers = ["akka.event.slf4j.Slf4jLogger"]
  logging-filter = "akka.event.slf4j.Slf4jLoggingFilter"
}
EOF

# Create Explorer API configuration
cat > api-config/application.conf << 'EOF'
explorer-api {
  postgres {
    url = "jdbc:postgresql://postgres:5432/explorer"
    user = "ergo"
    password = "ergo_password"
    schema = "public"
    
    # Connection pool settings
    hikari {
      maximumPoolSize = 20
      connectionTimeout = 5000
    }
  }
  
  # API settings
  service {
    host = "0.0.0.0"
    port = 8080
    
    # CORS settings
    cors {
      allowed-origins = ["*"]
      allowed-methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
      allowed-headers = ["*"]
      allow-credentials = true
    }
    
    # Request throttling
    throttling {
      enabled = false
      rate-per-second = 20
      burst = 100
    }
  }
  
  # Cache settings
  cache {
    # Redis can be used for caching in a production environment
    redis {
      enabled = false
      host = "localhost"
      port = 6379
    }
    
    # In-memory cache settings
    in-memory {
      enabled = true
      max-size = 1000
      expire-after-access = 1h
      expire-after-write = 2h
    }
  }
}

akka {
  http {
    server {
      request-timeout = 60s
      idle-timeout = 120s
    }
  }
  
  loglevel = "INFO"
  loggers = ["akka.event.slf4j.Slf4jLogger"]
  logging-filter = "akka.event.slf4j.Slf4jLoggingFilter"
}
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Ergo Node
  ergo-node:
    image: ergoplatform/ergo:latest
    container_name: ergo-node
    volumes:
      - ergo-data:/home/ergo/.ergo
      - ./node-config/ergo.conf:/home/ergo/.ergo/ergo.conf
    ports:
      - "9053:9053"
      - "9030:9030"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9053/info"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s

  # PostgreSQL Database for Explorer
  postgres:
    image: postgres:13
    container_name: ergo-postgres
    environment:
      POSTGRES_USER: ergo
      POSTGRES_PASSWORD: ergo_password
      POSTGRES_DB: explorer
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./db-init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ergo"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  # Chain Grabber to index blockchain data
  chain-grabber:
    build:
      context: .
      dockerfile: Dockerfile.chain-grabber
    container_name: ergo-chain-grabber
    depends_on:
      ergo-node:
        condition: service_healthy
      postgres:
        condition: service_healthy
    volumes:
      - ./grabber-config:/app/config
    restart: unless-stopped
    environment:
      - JAVA_OPTS=-Xmx2g

  # Explorer API service
  explorer-api:
    build:
      context: .
      dockerfile: Dockerfile.explorer-api
    container_name: ergo-explorer-api
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8080:8080"
    volumes:
      - ./api-config:/app/config
    restart: unless-stopped
    environment:
      - JAVA_OPTS=-Xmx1g

volumes:
  ergo-data:
  postgres-data:
EOF

# Create Dockerfile for Chain Grabber
cat > Dockerfile.chain-grabber << 'EOF'
# Multi-stage build for Ergo Chain Grabber
FROM openjdk:11-slim AS builder

# Install required dependencies
RUN apt-get update && \
    apt-get install -y curl git unzip

# Install SBT
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list && \
    echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list && \
    curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | apt-key add && \
    apt-get update && \
    apt-get install -y sbt

# Clone and build the explorer-backend repository
WORKDIR /build
RUN git clone https://github.com/ergoplatform/explorer-backend.git
WORKDIR /build/explorer-backend
RUN sbt "project chain-grabber" assembly

# Final stage
FROM openjdk:11-jre-slim

# Copy the built JAR from the builder stage
COPY --from=builder /build/explorer-backend/modules/chain-grabber/target/scala-2.12/chain-grabber-assembly-*.jar /app/chain-grabber.jar

# Create config directory
RUN mkdir -p /app/config

# Set the working directory
WORKDIR /app

# Define volume for configuration
VOLUME /app/config

# Command to run the application
ENTRYPOINT ["java", "-jar", "-Dconfig.file=/app/config/application.conf", "chain-grabber.jar"]
EOF

# Create Dockerfile for Explorer API
cat > Dockerfile.explorer-api << 'EOF'
# Multi-stage build for Ergo Explorer API
FROM openjdk:11-slim AS builder

# Install required dependencies
RUN apt-get update && \
    apt-get install -y curl git unzip

# Install SBT
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list && \
    echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list && \
    curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | apt-key add && \
    apt-get update && \
    apt-get install -y sbt

# Clone and build the explorer-backend repository
WORKDIR /build
RUN git clone https://github.com/ergoplatform/explorer-backend.git
WORKDIR /build/explorer-backend
RUN sbt "project explorer-api" assembly

# Final stage
FROM openjdk:11-jre-slim

# Copy the built JAR from the builder stage
COPY --from=builder /build/explorer-backend/modules/explorer-api/target/scala-2.12/explorer-api-assembly-*.jar /app/explorer-api.jar

# Create config directory
RUN mkdir -p /app/config

# Set the working directory
WORKDIR /app

# Define volume for configuration
VOLUME /app/config

# Expose the API port
EXPOSE 8080

# Command to run the application
ENTRYPOINT ["java", "-jar", "-Dconfig.file=/app/config/application.conf", "explorer-api.jar"]
EOF

echo "All configuration files created successfully."

# Create README.md
cat > README.md << 'EOF'
# Ergo Node and Indexer

This project provides a containerized setup for running an Ergo Node along with a blockchain indexer and explorer API. It allows you to have a fully functional Ergo blockchain database with search and query capabilities.

## Getting Started

1. Run the setup script to create all necessary files:
   ```bash
   ./setup.sh
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

The Ergo node will start syncing the blockchain, and the Chain Grabber will begin indexing once the node is healthy.

## Usage

Once the services are running, you can:

- Access the Ergo Node API at `http://localhost:9053`
- Access the Explorer API at `http://localhost:8080`
- Connect to the PostgreSQL database at `localhost:5432` with credentials:
  - Username: `ergo`
  - Password: `ergo_password`
  - Database: `explorer`

See the documentation for more details.
EOF

echo "Setup complete. You can now run 'docker-compose up -d' to start the services."