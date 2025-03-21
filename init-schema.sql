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