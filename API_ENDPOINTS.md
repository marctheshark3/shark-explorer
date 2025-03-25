# Shark Explorer API Documentation

This document provides detailed information about the available API endpoints in the Shark Explorer.

## Base URL

All API endpoints are relative to the base URL:

```
http://your-server-address:8080/api
```

## Authentication

Currently, the API does not require authentication.

## Rate Limiting

Basic rate limiting is applied to prevent abuse. The default limit is 100 requests per minute per IP address.

## Endpoints

### Blocks

#### Get Latest Block

```
GET /blocks/latest
```

Returns the most recently indexed block.

**Response Example:**

```json
{
  "id": "b263842ce21c607296f8f77e5ae1951113e1f4c1e858cb0f3655234a5aaf721a",
  "height": 834582,
  "timestamp": 1652345678000,
  "transactionsCount": 12,
  "size": 2345,
  "difficulty": "5426732086152952",
  "minerReward": 67500000000
}
```

#### Get Block by Height

```
GET /blocks/{height}
```

**Parameters:**

- `height` (integer, required): The block height

**Response:** Same as Get Latest Block

#### Get Block by Header ID

```
GET /blocks/header/{headerId}
```

**Parameters:**

- `headerId` (string, required): The block header ID

**Response:** Same as Get Latest Block

### Transactions

#### Get Transaction by ID

```
GET /transactions/{txId}
```

**Parameters:**

- `txId` (string, required): The transaction ID

**Response Example:**

```json
{
  "id": "bb2b1beadbed1d16e6bc6d5f487798a481da8ee3454886aa73969e7270a3fbaa",
  "headerId": "b263842ce21c607296f8f77e5ae1951113e1f4c1e858cb0f3655234a5aaf721a",
  "inclusionHeight": 834582,
  "timestamp": 1652345678000,
  "index": 1,
  "confirmationsCount": 100,
  "inputs": [...],
  "outputs": [...]
}
```

#### Get Transaction Inputs

```
GET /transactions/{txId}/inputs
```

**Parameters:**

- `txId` (string, required): The transaction ID

**Response Example:**

```json
[
  {
    "id": "e91cbc48a5169c1e927347074b6c66d8158322591a872ebb8e71c61b5a24b9fd",
    "address": "9f4QF8AD1nQyxDZ8TKMd5tFeyLunUEwQHX8KGPtXx6pQXRVA67b",
    "value": 1000000000,
    "index": 0,
    "spendingProof": {
      "proofBytes": "639305c65c486412ee...",
      "extension": {}
    },
    "transactionId": "bb2b1beadbed1d16e6bc6d5f487798a481da8ee3454886aa73969e7270a3fbaa"
  }
]
```

#### Get Transaction Outputs

```
GET /transactions/{txId}/outputs
```

**Parameters:**

- `txId` (string, required): The transaction ID

**Response Example:**

```json
[
  {
    "id": "f5de46d8c6d5af9b6a82f8d5eaef9975b864c5a33fbdc29c4ca481c20cb98458",
    "txId": "bb2b1beadbed1d16e6bc6d5f487798a481da8ee3454886aa73969e7270a3fbaa",
    "value": 998000000,
    "index": 0,
    "creationHeight": 834582,
    "ergoTree": "0008cd0386aa...",
    "address": "9f4QF8AD1nQyxDZ8TKMd5tFeyLunUEwQHX8KGPtXx6pQXRVA67b",
    "assets": [],
    "additionalRegisters": {}
  }
]
```

### Addresses

#### Get Address Information

```
GET /addresses/{address}
```

**Parameters:**

- `address` (string, required): The Ergo address

**Response Example:**

```json
{
  "address": "9f4QF8AD1nQyxDZ8TKMd5tFeyLunUEwQHX8KGPtXx6pQXRVA67b",
  "balance": {
    "confirmed": 123456789,
    "unconfirmed": 0
  },
  "transactions": {
    "total": 42,
    "confirmedCount": 42
  }
}
```

#### Get Address Transactions

```
GET /addresses/{address}/transactions
```

**Parameters:**

- `address` (string, required): The Ergo address
- `limit` (integer, optional): Number of items to return (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response Example:**

```json
{
  "items": [
    {
      "id": "bb2b1beadbed1d16e6bc6d5f487798a481da8ee3454886aa73969e7270a3fbaa",
      "headerId": "b263842ce21c607296f8f77e5ae1951113e1f4c1e858cb0f3655234a5aaf721a",
      "inclusionHeight": 834582,
      "timestamp": 1652345678000,
      "value": 123456789
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

#### Get Address Balance

```
GET /addresses/{address}/balance
```

**Parameters:**

- `address` (string, required): The Ergo address

**Response Example:**

```json
{
  "address": "9f4QF8AD1nQyxDZ8TKMd5tFeyLunUEwQHX8KGPtXx6pQXRVA67b",
  "balance": 123456789,
  "assets": [
    {
      "tokenId": "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",
      "amount": 100
    }
  ]
}
```

### Tokens

#### Get Token Holders

```
GET /tokens/{tokenId}/holders
```

**Parameters:**

- `tokenId` (string, required): The token ID
- `limit` (integer, optional): Number of holders to return (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response Example:**

```json
{
  "token": {
    "tokenId": "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",
    "name": "SigUSD",
    "description": "SigmaUSD stablecoin",
    "decimals": 2,
    "totalSupply": 5000000
  },
  "holders": [
    {
      "address": "9f4QF8AD1nQyxDZ8TKMd5tFeyLunUEwQHX8KGPtXx6pQXRVA67b",
      "balance": 1000000,
      "percentage": 20.0
    },
    {
      "address": "9hY16AdX7kSS4YkQsZwTwyNYctKSxZFxPQ72AqjJi9NfHEYAif7",
      "balance": 500000,
      "percentage": 10.0
    }
  ],
  "total": 156,
  "limit": 20,
  "offset": 0
}
```

#### Get Top Tokens by Holder Count

```
GET /tokens/top
```

**Parameters:**

- `limit` (integer, optional): Number of tokens to return (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response Example:**

```json
{
  "tokens": [
    {
      "tokenId": "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",
      "name": "SigUSD",
      "description": "SigmaUSD stablecoin",
      "decimals": 2,
      "totalSupply": 5000000,
      "holderCount": 1567
    },
    {
      "tokenId": "d71693c49a84fbbecd4908c94813b46514b18b67a99952dc1e6e4791556de413",
      "name": "ErgoMixer Token",
      "description": "Official ErgoMixer Token",
      "decimals": 0,
      "totalSupply": 1000000,
      "holderCount": 982
    }
  ],
  "total": 1205,
  "limit": 20,
  "offset": 0
}
```

#### Get Address Tokens

```
GET /tokens/address/{address}
```

**Parameters:**

- `address` (string, required): The Ergo address
- `limit` (integer, optional): Number of tokens to return (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response Example:**

```json
{
  "address": "9f4QF8AD1nQyxDZ8TKMd5tFeyLunUEwQHX8KGPtXx6pQXRVA67b",
  "tokens": [
    {
      "tokenId": "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",
      "name": "SigUSD",
      "description": "SigmaUSD stablecoin",
      "decimals": 2,
      "balance": 1000000
    },
    {
      "tokenId": "d71693c49a84fbbecd4908c94813b46514b18b67a99952dc1e6e4791556de413",
      "name": "ErgoMixer Token",
      "description": "Official ErgoMixer Token",
      "decimals": 0,
      "balance": 100
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

### Info

#### Get Indexer Status

```
GET /info/status
```

**Response Example:**

```json
{
  "currentHeight": 834582,
  "nodeHeight": 834583,
  "isSynced": true,
  "syncProgress": 99.9,
  "version": "1.0.0",
  "uptime": 345678
}
```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests.

### Common Error Codes

- `400 Bad Request`: The request was malformed or invalid
- `404 Not Found`: The requested resource was not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: An unexpected error occurred on the server

### Error Response Format

```json
{
  "status": 404,
  "error": "Not Found",
  "message": "Transaction with ID '1234567890' not found"
}
```

## Pagination

Endpoints that return potentially large collections support pagination using `limit` and `offset` parameters:

- `limit`: Number of items to return per page
- `offset`: Number of items to skip (starting point)

Response objects for paginated endpoints include `total`, `limit`, and `offset` fields to facilitate navigation. 