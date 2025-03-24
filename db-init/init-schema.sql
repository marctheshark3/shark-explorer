-- Create tables and indexes for the Ergo Explorer database
-- This schema is based on the explorer-backend project's schema

-- Core Tables for Ergo Explorer

-- Blocks table
CREATE TABLE blocks (
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    header_id VARCHAR(64) NOT NULL,
    parent_id VARCHAR(64),
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
    version INTEGER NOT NULL,
    transactions_root VARCHAR(64),
    state_root VARCHAR(64),
    pow_solutions JSONB,
    CONSTRAINT blocks_height_key UNIQUE (height)
);

CREATE INDEX blocks_height_idx ON blocks(height);
CREATE INDEX blocks_timestamp_idx ON blocks(timestamp);

-- Transactions table
CREATE TABLE transactions (
    id VARCHAR(64) PRIMARY KEY,
    block_id VARCHAR(64) NOT NULL REFERENCES blocks(id),
    header_id VARCHAR(64) NOT NULL,
    inclusion_height INTEGER NOT NULL,
    timestamp BIGINT NOT NULL,
    index INTEGER NOT NULL,
    main_chain BOOLEAN NOT NULL,
    size INTEGER NOT NULL,
    fee BIGINT,
    status VARCHAR(20) DEFAULT 'confirmed'
);

CREATE INDEX transactions_block_id_idx ON transactions(block_id);
CREATE INDEX transactions_timestamp_idx ON transactions(timestamp);

-- Inputs table
CREATE TABLE inputs (
    box_id VARCHAR(64) NOT NULL,
    tx_id VARCHAR(64) NOT NULL,
    index_in_tx INTEGER NOT NULL,
    proof_bytes TEXT,
    extension JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (box_id, tx_id),
    CONSTRAINT inputs_tx_id_fk FOREIGN KEY (tx_id) REFERENCES transactions(id)
);

CREATE INDEX inputs_tx_id_idx ON inputs(tx_id);

-- Outputs table
CREATE TABLE outputs (
    box_id VARCHAR(64) PRIMARY KEY,
    tx_id VARCHAR(64) NOT NULL,
    index_in_tx INTEGER NOT NULL,
    value BIGINT NOT NULL,
    creation_height INTEGER NOT NULL,
    address VARCHAR(64),
    ergo_tree TEXT NOT NULL,
    additional_registers JSON,
    spent_by_tx_id VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT outputs_tx_id_fk FOREIGN KEY (tx_id) REFERENCES transactions(id),
    CONSTRAINT outputs_spent_by_tx_id_fk FOREIGN KEY (spent_by_tx_id) REFERENCES transactions(id)
);

CREATE INDEX outputs_tx_id_idx ON outputs(tx_id);
CREATE INDEX outputs_address_idx ON outputs(address);
CREATE INDEX outputs_spent_by_tx_id_idx ON outputs(spent_by_tx_id);

-- Assets table
CREATE TABLE assets (
    id VARCHAR(128) PRIMARY KEY,
    box_id VARCHAR(64) NOT NULL,
    index_in_outputs INTEGER NOT NULL,
    token_id VARCHAR(64) NOT NULL,
    amount BIGINT NOT NULL,
    name VARCHAR(255),
    decimals INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT assets_box_id_fk FOREIGN KEY (box_id) REFERENCES outputs(box_id)
);

CREATE INDEX assets_token_id_idx ON assets(token_id);
CREATE INDEX assets_box_id_idx ON assets(box_id);

-- Metadata Tables

-- Token Info table
CREATE TABLE token_info (
    token_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    decimals INTEGER,
    total_supply BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX token_info_name_idx ON token_info(name);

-- Sync Status table
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_height INTEGER NOT NULL,
    target_height INTEGER NOT NULL,
    is_syncing BOOLEAN DEFAULT false,
    last_block_time BIGINT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sync_status_single_row CHECK (id = 1)
);

-- Mining Rewards table
CREATE TABLE mining_rewards (
    block_id VARCHAR(64) PRIMARY KEY,
    reward_amount BIGINT NOT NULL,
    fees_amount BIGINT NOT NULL,
    miner_address VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT mining_rewards_block_id_fk FOREIGN KEY (block_id) REFERENCES blocks(id)
);

-- Views

-- Address Balances view
CREATE VIEW address_balances AS
SELECT 
    address,
    SUM(CASE WHEN spent_by_tx_id IS NULL THEN value ELSE 0 END) as confirmed_balance,
    COUNT(DISTINCT tx_id) as total_transactions
FROM outputs
WHERE address IS NOT NULL
GROUP BY address;

-- Token Balances view
CREATE VIEW token_balances AS
SELECT 
    o.address,
    a.token_id,
    SUM(a.amount) as amount,
    t.name as token_name,
    t.decimals
FROM outputs o
JOIN assets a ON o.box_id = a.box_id
LEFT JOIN token_info t ON a.token_id = t.token_id
WHERE o.spent_by_tx_id IS NULL
GROUP BY o.address, a.token_id, t.name, t.decimals;

-- Asset Metadata table
CREATE TABLE asset_metadata (
    token_id VARCHAR(64) PRIMARY KEY,
    asset_type VARCHAR(32),
    issuer_address VARCHAR(64),
    minting_tx_id VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT asset_metadata_token_id_fk FOREIGN KEY (token_id) REFERENCES token_info(token_id),
    CONSTRAINT asset_metadata_minting_tx_fk FOREIGN KEY (minting_tx_id) REFERENCES transactions(id)
);

-- Address Stats table
CREATE TABLE address_stats (
    address VARCHAR(64) PRIMARY KEY,
    first_active_time BIGINT,
    last_active_time BIGINT,
    address_type VARCHAR(32),
    script_complexity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE blocks ADD CONSTRAINT blocks_parent_id_fk FOREIGN KEY (parent_id) REFERENCES blocks(id);