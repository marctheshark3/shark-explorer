# Ergo Explorer Database Documentation

## Core Tables

### blocks
Primary table for storing block information from the Ergo blockchain.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | VARCHAR(64) | Block ID/hash | PRIMARY KEY |
| header_id | VARCHAR(64) | Block header ID | NOT NULL |
| parent_id | VARCHAR(64) | Parent block ID | FOREIGN KEY |
| height | INTEGER | Block height | NOT NULL, UNIQUE |
| timestamp | BIGINT | Block timestamp | NOT NULL |
| difficulty | BIGINT | Mining difficulty | NOT NULL |
| block_size | INTEGER | Size in bytes | NOT NULL |
| block_coins | BIGINT | Total coins in block | NOT NULL |
| block_mining_time | BIGINT | Time taken to mine | |
| txs_count | INTEGER | Number of transactions | NOT NULL |
| txs_size | INTEGER | Total size of transactions | NOT NULL |
| miner_address | VARCHAR(64) | Miner's address | |
| miner_name | VARCHAR(128) | Miner's name/pool | |
| main_chain | BOOLEAN | Is in main chain | NOT NULL |
| version | INTEGER | Block version | NOT NULL |
| transactions_root | VARCHAR(64) | Merkle root of transactions | |
| state_root | VARCHAR(64) | State root hash | |
| pow_solutions | JSONB | Proof of work details | |

**Indexes:**
- `blocks_height_idx` on (height)
- `blocks_timestamp_idx` on (timestamp)

### transactions
Stores all transactions in the blockchain.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | VARCHAR(64) | Transaction ID | PRIMARY KEY |
| block_id | VARCHAR(64) | Block containing tx | NOT NULL, FOREIGN KEY |
| header_id | VARCHAR(64) | Block header ID | NOT NULL |
| inclusion_height | INTEGER | Block height | NOT NULL |
| timestamp | BIGINT | Transaction timestamp | NOT NULL |
| index | INTEGER | Position in block | NOT NULL |
| main_chain | BOOLEAN | Is in main chain | NOT NULL |
| size | INTEGER | Size in bytes | NOT NULL |
| fee | BIGINT | Transaction fee | |
| status | VARCHAR(20) | Transaction status | DEFAULT 'confirmed' |

**Indexes:**
- `transactions_block_id_idx` on (block_id)
- `transactions_timestamp_idx` on (timestamp)

### inputs
Records transaction inputs.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| box_id | VARCHAR(64) | Input box ID | PRIMARY KEY (with tx_id) |
| tx_id | VARCHAR(64) | Transaction ID | PRIMARY KEY (with box_id), FOREIGN KEY |
| index_in_tx | INTEGER | Input position | NOT NULL |
| proof_bytes | TEXT | Proof data | |
| extension | JSON | Additional data | |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |

**Indexes:**
- `inputs_tx_id_idx` on (tx_id)

### outputs
Records transaction outputs (boxes).

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| box_id | VARCHAR(64) | Output box ID | PRIMARY KEY |
| tx_id | VARCHAR(64) | Creating transaction | NOT NULL, FOREIGN KEY |
| index_in_tx | INTEGER | Output position | NOT NULL |
| value | BIGINT | ERG amount | NOT NULL |
| creation_height | INTEGER | Creation block height | NOT NULL |
| address | VARCHAR(64) | Recipient address | |
| ergo_tree | TEXT | Box script | NOT NULL |
| additional_registers | JSON | Additional registers | |
| spent_by_tx_id | VARCHAR(64) | Spending transaction | FOREIGN KEY |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |

**Indexes:**
- `outputs_tx_id_idx` on (tx_id)
- `outputs_address_idx` on (address)
- `outputs_spent_by_tx_id_idx` on (spent_by_tx_id)

### assets
Tracks token transfers and information.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | VARCHAR(128) | Asset record ID | PRIMARY KEY |
| box_id | VARCHAR(64) | Containing box | NOT NULL, FOREIGN KEY |
| index_in_outputs | INTEGER | Position in outputs | NOT NULL |
| token_id | VARCHAR(64) | Token identifier | NOT NULL |
| amount | BIGINT | Token amount | NOT NULL |
| name | VARCHAR(255) | Token name | |
| decimals | INTEGER | Token decimals | |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |

**Indexes:**
- `assets_token_id_idx` on (token_id)
- `assets_box_id_idx` on (box_id)

## Metadata Tables

### token_info
Stores detailed token information.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| token_id | VARCHAR(64) | Token identifier | PRIMARY KEY |
| name | VARCHAR(255) | Token name | |
| description | TEXT | Token description | |
| decimals | INTEGER | Token decimals | |
| total_supply | BIGINT | Total token supply | |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | Last update time | DEFAULT CURRENT_TIMESTAMP |

**Indexes:**
- `token_info_name_idx` on (name)

### mining_rewards
Tracks mining rewards per block.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| block_id | VARCHAR(64) | Block ID | PRIMARY KEY, FOREIGN KEY |
| reward_amount | BIGINT | Block reward | NOT NULL |
| fees_amount | BIGINT | Total fees | NOT NULL |
| miner_address | VARCHAR(64) | Recipient address | |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |

### asset_metadata
Extended token metadata.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| token_id | VARCHAR(64) | Token identifier | PRIMARY KEY, FOREIGN KEY |
| asset_type | VARCHAR(32) | Token type | |
| issuer_address | VARCHAR(64) | Issuer's address | |
| minting_tx_id | VARCHAR(64) | Creation transaction | FOREIGN KEY |
| metadata | JSONB | Additional metadata | |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |

### address_stats
Address statistics and metadata.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| address | VARCHAR(64) | Ergo address | PRIMARY KEY |
| first_active_time | BIGINT | First transaction time | |
| last_active_time | BIGINT | Latest transaction time | |
| address_type | VARCHAR(32) | Address type | |
| script_complexity | INTEGER | Script complexity score | |
| created_at | TIMESTAMP | Record creation time | DEFAULT CURRENT_TIMESTAMP |

### sync_status
Tracks indexer synchronization status.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | INTEGER | Status record ID | PRIMARY KEY, DEFAULT 1 |
| current_height | INTEGER | Current sync height | NOT NULL |
| target_height | INTEGER | Target sync height | NOT NULL |
| is_syncing | BOOLEAN | Sync in progress | DEFAULT false |
| last_block_time | BIGINT | Last block timestamp | |
| updated_at | TIMESTAMP | Last update time | DEFAULT CURRENT_TIMESTAMP |

## Views

### address_balances
Calculates current address balances.

```sql
SELECT 
    address,
    SUM(CASE WHEN spent_by_tx_id IS NULL THEN value ELSE 0 END) as confirmed_balance,
    COUNT(DISTINCT tx_id) as total_transactions
FROM outputs
WHERE address IS NOT NULL
GROUP BY address
```

### token_balances
Calculates current token balances per address.

```sql
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
GROUP BY o.address, a.token_id, t.name, t.decimals
``` 