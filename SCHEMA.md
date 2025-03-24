# Database Schema Design

## Core Tables

### blocks
```sql
CREATE TABLE blocks (
    id VARCHAR(64) PRIMARY KEY,
    height INTEGER NOT NULL UNIQUE,
    timestamp BIGINT NOT NULL,
    parent_id VARCHAR(64) NOT NULL,
    difficulty BIGINT NOT NULL,
    block_size INTEGER NOT NULL,
    extension_hash VARCHAR(64),
    miner_pk VARCHAR(64),
    w VARCHAR(64),
    n VARCHAR(64),
    d NUMERIC,
    votes VARCHAR(3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT blocks_parent_id_fk FOREIGN KEY (parent_id) REFERENCES blocks(id)
);

CREATE INDEX blocks_height_idx ON blocks(height);
CREATE INDEX blocks_timestamp_idx ON blocks(timestamp);
```

### transactions

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(64) | Primary key - transaction ID |
| block_id | VARCHAR(64) | Foreign key to blocks table |
| header_id | VARCHAR(64) | Block header ID |
| inclusion_height | INTEGER | Height at which transaction was included |
| timestamp | BIGINT | Transaction timestamp |
| index | INTEGER | Index of transaction in block |
| main_chain | BOOLEAN | Whether transaction is in main chain |
| size | INTEGER | Transaction size in bytes |
```sql
CREATE TABLE transactions (
    id VARCHAR(64) PRIMARY KEY,
    block_id VARCHAR(64) NOT NULL,
    header_id VARCHAR(64),
    inclusion_height INTEGER,
    timestamp BIGINT NOT NULL,
    index INTEGER NOT NULL,
    main_chain BOOLEAN,
    size INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT transactions_block_id_fk FOREIGN KEY (block_id) REFERENCES blocks(id)
);

CREATE INDEX transactions_block_id_idx ON transactions(block_id);
CREATE INDEX transactions_timestamp_idx ON transactions(timestamp);
```

### inputs
```sql
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
```

### outputs
```sql
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
```

### assets
```sql
CREATE TABLE assets (
    id VARCHAR(64) PRIMARY KEY,
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
```

## Metadata Tables

### token_info
```sql
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
```

### sync_status
```sql
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_height INTEGER NOT NULL,
    target_height INTEGER NOT NULL,
    is_syncing BOOLEAN DEFAULT false,
    last_block_time BIGINT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sync_status_single_row CHECK (id = 1)
);
```

## Views

### address_balances
```sql
CREATE VIEW address_balances AS
SELECT 
    address,
    SUM(CASE WHEN spent_by_tx_id IS NULL THEN value ELSE 0 END) as confirmed_balance,
    COUNT(DISTINCT tx_id) as total_transactions
FROM outputs
WHERE address IS NOT NULL
GROUP BY address;
```

### token_balances
```sql
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
``` 