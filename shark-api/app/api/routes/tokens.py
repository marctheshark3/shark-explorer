"""
Token related API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List, Dict, Any
import asyncpg
from ..database import get_db
from ..models.token import (
    TokenHolderResponse,
    TopTokensResponse,
    AddressTokensResponse
)
from ..metrics import track_request, track_db_query

router = APIRouter(
    prefix="/tokens",
    tags=["tokens"],
)


@router.get("/{token_id}/holders", response_model=TokenHolderResponse)
async def get_token_holders(
    token_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db)
):
    """
    Get a list of token holders for a specific token.
    
    Parameters:
    - token_id: The ID of the token
    - limit: Number of holders to return (default: 20, max: 100)
    - offset: Pagination offset
    
    Returns:
    - Token information and a list of holders with their balances
    """
    with track_request("GET", f"/tokens/{token_id}/holders"):
        try:
            with track_db_query("get_token_holders"):
                # Call the stored procedure to get token holders
                result = await conn.fetchval(
                    "SELECT get_token_holders($1, $2, $3)",
                    token_id, limit, offset
                )
                
                # Check if the result contains an error
                if result and isinstance(result, dict) and 'error' in result:
                    if result.get('status') == 404:
                        raise HTTPException(status_code=404, detail="Token not found")
                    else:
                        raise HTTPException(
                            status_code=result.get('status', 500),
                            detail=result.get('error', "Unknown error")
                        )
                
                return result
        except asyncpg.PostgresError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )


@router.get("/top", response_model=TopTokensResponse)
async def get_top_tokens(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db)
):
    """
    Get a list of top tokens by holder count.
    
    Parameters:
    - limit: Number of tokens to return (default: 20, max: 100)
    - offset: Pagination offset
    
    Returns:
    - List of tokens with their holder counts
    """
    with track_request("GET", "/tokens/top"):
        try:
            with track_db_query("get_top_tokens"):
                # Call the stored procedure to get top tokens
                result = await conn.fetchval(
                    "SELECT get_top_tokens($1, $2)",
                    limit, offset
                )
                
                return result
        except asyncpg.PostgresError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )


@router.get("/address/{address}", response_model=AddressTokensResponse)
async def get_address_tokens(
    address: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db)
):
    """
    Get a list of tokens owned by an address.
    
    Parameters:
    - address: The address to query
    - limit: Number of tokens to return (default: 20, max: 100)
    - offset: Pagination offset
    
    Returns:
    - List of tokens with balances
    """
    with track_request("GET", f"/tokens/address/{address}"):
        try:
            with track_db_query("get_address_tokens"):
                # Call the stored procedure to get address tokens
                result = await conn.fetchval(
                    "SELECT get_address_tokens($1, $2, $3)",
                    address, limit, offset
                )
                
                return result
        except asyncpg.PostgresError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            ) 