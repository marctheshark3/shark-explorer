# Token Holder API Endpoints

This document outlines the API endpoints for retrieving token holder information.

## Token Holders List

Get a list of all addresses holding a specific token.

### Endpoint

```
GET /tokens/{tokenId}/holders
```

### Parameters

| Name       | Type   | Required | Description                                      |
|------------|--------|----------|--------------------------------------------------|
| tokenId    | string | Yes      | Token ID                                         |
| limit      | int    | No       | Maximum number of results (default: 20, max: 100)|
| offset     | int    | No       | Offset for pagination (default: 0)               |
| sortBy     | string | No       | Sort field (amount, address) (default: amount)   |
| sortOrder  | string | No       | Sort order (asc, desc) (default: desc)           |
| minAmount  | long   | No       | Minimum token amount filter                      |
| maxAmount  | long   | No       | Maximum token amount filter                      |

### Response

```json
{
  "total": 150,
  "items": [
    {
      "address": "9f4QF8AD1nQ3nJahQVkMj8hFSVVzVom77b52JU7EW71Zexg6N8v",
      "amount": "1000000",
      "percentage": "10.5",
      "lastUpdated": "2023-06-15T10:30:45Z"
    },
    {
      "address": "9h3DsPKkND2oLC9JXz7ztKFgFi3UfX5peARRvnGLpEFn5fNjK2K",
      "amount": "500000",
      "percentage": "5.25",
      "lastUpdated": "2023-06-12T08:15:30Z"
    }
  ]
}
```

## Token Rich List

Get a rich list for a specific token (sorted by amount held).

### Endpoint

```
GET /tokens/{tokenId}/rich-list
```

### Parameters

| Name       | Type   | Required | Description                                      |
|------------|--------|----------|--------------------------------------------------|
| tokenId    | string | Yes      | Token ID                                         |
| limit      | int    | No       | Maximum number of results (default: 100, max: 500)|
| offset     | int    | No       | Offset for pagination (default: 0)               |
| minAmount  | long   | No       | Minimum token amount filter                      |

### Response

```json
{
  "total": 150,
  "tokenInfo": {
    "id": "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0",
    "name": "SigmaUSD",
    "decimals": 2,
    "supply": "10000000"
  },
  "items": [
    {
      "address": "9f4QF8AD1nQ3nJahQVkMj8hFSVVzVom77b52JU7EW71Zexg6N8v",
      "amount": "1000000",
      "percentage": "10.5"
    },
    {
      "address": "9h3DsPKkND2oLC9JXz7ztKFgFi3UfX5peARRvnGLpEFn5fNjK2K",
      "amount": "500000",
      "percentage": "5.25"
    }
  ]
}
```

## Token Distribution Statistics

Get distribution statistics for a token.

### Endpoint

```
GET /tokens/{tokenId}/distribution
```

### Parameters

| Name       | Type   | Required | Description                                      |
|------------|--------|----------|--------------------------------------------------|
| tokenId    | string | Yes      | Token ID                                         |

### Response

```json
{
  "tokenId": "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0",
  "name": "SigmaUSD",
  "totalHolders": 150,
  "totalSupply": "10000000",
  "circulatingSupply": "9500000",
  "distribution": {
    "top10Addresses": {
      "count": 10,
      "percentage": 45.3,
      "amount": "4530000"
    },
    "top50Addresses": {
      "count": 50,
      "percentage": 78.2,
      "amount": "7820000"
    },
    "top100Addresses": {
      "count": 100,
      "percentage": 94.5,
      "amount": "9450000"
    }
  },
  "ranges": [
    {
      "range": "1-100",
      "holders": 80,
      "percentage": 0.8
    },
    {
      "range": "101-1000",
      "holders": 40,
      "percentage": 3.5
    },
    {
      "range": "1001-10000",
      "holders": 20,
      "percentage": 15.7
    },
    {
      "range": "10001+",
      "holders": 10,
      "percentage": 80.0
    }
  ]
}
```

## Export Token Holders

Export a list of token holders for airdrops or other purposes.

### Endpoint

```
GET /tokens/{tokenId}/export
```

### Parameters

| Name       | Type   | Required | Description                                      |
|------------|--------|----------|--------------------------------------------------|
| tokenId    | string | Yes      | Token ID                                         |
| format     | string | No       | Export format (csv, json) (default: csv)         |
| minAmount  | long   | No       | Minimum token amount filter                      |
| snapshot   | string | No       | Optional snapshot timestamp (YYYY-MM-DDThh:mm:ssZ) |

### Response

For CSV format, a downloadable CSV file with the following columns:
- address
- amount
- percentage

For JSON format:
```json
{
  "tokenId": "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0",
  "name": "SigmaUSD",
  "exportTimestamp": "2023-06-20T15:30:45Z",
  "snapshot": "2023-06-20T00:00:00Z",
  "holders": [
    {
      "address": "9f4QF8AD1nQ3nJahQVkMj8hFSVVzVom77b52JU7EW71Zexg6N8v",
      "amount": "1000000",
      "percentage": "10.5"
    },
    {
      "address": "9h3DsPKkND2oLC9JXz7ztKFgFi3UfX5peARRvnGLpEFn5fNjK2K",
      "amount": "500000",
      "percentage": "5.25"
    }
  ]
}
```

## Implementation Considerations

### Database Schema

The following schema changes will be required to efficiently support these endpoints:

1. New table: `token_holders`
   - token_id (string, indexed)
   - address (string, indexed)
   - amount (bigint)
   - last_updated (timestamp)

2. Indexes:
   - Combined index on (token_id, amount) for efficient rich list queries
   - Combined index on (token_id, address) for efficient holder lookup

### Performance Optimization

1. For tokens with a large number of holders:
   - Implement caching for rich list and distribution statistics
   - Use materialized views or pre-calculated statistics updated periodically
   - Consider pagination and limit parameters to reduce response size

2. For real-time data:
   - Update the token_holders table when processing transactions
   - Maintain a history of changes for snapshot functionality

### Monitoring and Metrics

1. Track API usage:
   - Most queried tokens
   - Response times for large holder lists
   - Export frequency

2. Alert on:
   - Long-running queries
   - High memory usage during exports
   - Timeouts for large token holder queries 