# Ergo Custom Indexing Service API Specification

## API Endpoints

### Blocks

#### GET /api/v1/blocks/latest
Get the latest block information
```json
{
  "height": 1000000,
  "id": "block_hash",
  "timestamp": 1234567890,
  "transactions": ["tx1", "tx2"]
}
```

#### GET /api/v1/blocks/{height}
Get block by height
```json
{
  "height": 1000000,
  "id": "block_hash",
  "timestamp": 1234567890,
  "transactions": ["tx1", "tx2"]
}
```

#### GET /api/v1/blocks/{hash}
Get block by hash
```json
{
  "height": 1000000,
  "id": "block_hash",
  "timestamp": 1234567890,
  "transactions": ["tx1", "tx2"]
}
```

### Transactions

#### GET /api/v1/transactions/{txId}
Get transaction details
```json
{
  "id": "tx_hash",
  "blockId": "block_hash",
  "timestamp": 1234567890,
  "inputs": [],
  "outputs": [],
  "assets": []
}
```

#### GET /api/v1/addresses/{address}/transactions
Get address transactions
```json
{
  "items": [
    {
      "id": "tx_hash",
      "timestamp": 1234567890,
      "type": "input/output",
      "value": 1000000
    }
  ],
  "total": 100
}
```

### Addresses

#### GET /api/v1/addresses/{address}
Get address information
```json
{
  "address": "address",
  "balance": 1000000,
  "transactions": 100,
  "assets": []
}
```

#### GET /api/v1/addresses/{address}/balance
Get address balance
```json
{
  "confirmed": 1000000,
  "unconfirmed": 0,
  "assets": []
}
```

### Assets

#### GET /api/v1/assets/{assetId}
Get asset information
```json
{
  "id": "asset_id",
  "name": "Asset Name",
  "decimals": 0,
  "totalSupply": 1000000
}
```

#### GET /api/v1/assets/search
Search assets
```json
{
  "items": [
    {
      "id": "asset_id",
      "name": "Asset Name"
    }
  ],
  "total": 100
}
```

### Search

#### GET /api/v1/search?q={query}
Search blocks, transactions, addresses
```json
{
  "blocks": [],
  "transactions": [],
  "addresses": []
}
```

### Status

#### GET /api/v1/status
Get indexer status
```json
{
  "height": 1000000,
  "synced": true,
  "processing": false,
  "lastBlockTime": 1234567890
}
```

## Error Responses
All endpoints use standard HTTP status codes and return errors in the format:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

## Rate Limiting
- Default: 60 requests per minute
- Authenticated: 1000 requests per minute
- Status Code: 429 Too Many Requests 