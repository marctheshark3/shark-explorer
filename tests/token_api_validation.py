#!/usr/bin/env python3
"""
Token API Validation Script

This script tests the token-related API endpoints for the Shark Explorer.
It validates that the token holder endpoints are working correctly and
provides detailed feedback on any issues encountered.
"""

import requests
import json
import sys
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("token_api_validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("token_api_validation")

# Known addresses with tokens for testing
known_addresses = [
    "9hXmgvzndtakdVzNUYYcJXRF7UyGjm6Dq4KtdkG8yf3xU7HIrK1",
    "9hyDXH72HoNTiG2pvxFQwxAhWqXGkB6xDRMuaasLnXuWmxeGJEw"
]

class TokenAPIValidator:
    """Class to validate the token API endpoints."""
    
    def __init__(self, api_url: str, node_url: Optional[str] = None):
        """
        Initialize the validator with API URLs.
        
        Args:
            api_url: URL of the Shark Explorer API
            node_url: Optional URL of the Ergo node for comparison
        """
        self.api_url = api_url.rstrip("/") + "/api/v1"  # Ensure API URL has /api/v1 prefix
        self.node_url = node_url.rstrip('/') if node_url else None
        self.session = requests.Session()
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        logger.info(f"Initializing validator with API URL: {api_url}")
        if node_url:
            logger.info(f"Using node URL for comparison: {node_url}")
    
    def run_all_tests(self) -> bool:
        """Run all token API validation tests."""
        logger.info("Starting token API validation tests...")
        start_time = time.time()
        
        # Get tokens from address test
        try:
            # First, get a random address with tokens from the API
            address = self._get_address_with_tokens()
            if address:
                self._test_address_tokens(address)
            else:
                logger.warning("Could not find an address with tokens")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing address tokens: {str(e)}")
            self.failed_tests += 1
        
        # Get token holders test
        try:
            # Get a token ID to test
            token_id = self._get_token_id()
            if token_id:
                self._test_token_holders(token_id)
            else:
                logger.warning("Could not find a token ID to test")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing token holders: {str(e)}")
            self.failed_tests += 1
        
        # Test top tokens endpoint
        try:
            self._test_top_tokens()
        except Exception as e:
            logger.error(f"Error testing top tokens: {str(e)}")
            self.failed_tests += 1
        
        # Get edge cases
        try:
            self._test_edge_cases()
        except Exception as e:
            logger.error(f"Error testing edge cases: {str(e)}")
            self.failed_tests += 1
        
        execution_time = time.time() - start_time
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        logger.info(f"Token API validation completed in {execution_time:.2f} seconds")
        logger.info(f"Total tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {self.failed_tests}")
        logger.info(f"Success rate: {success_rate:.2f}%")
        
        return self.failed_tests == 0
    
    def _get_address_with_tokens(self) -> Optional[str]:
        """Find an address that has tokens to test with."""
        logger.info("Looking for an address with tokens...")
        
        # Try to get a recent transaction first
        try:
            response = self.session.get(f"{self.api_url}/blocks/latest")
            if response.status_code == 200:
                latest_block = response.json()
                height = latest_block.get("height")
                
                # Get some blocks to look through
                for h in range(height, height - 10, -1):
                    block_response = self.session.get(f"{self.api_url}/blocks/{h}")
                    if block_response.status_code == 200:
                        block = block_response.json()
                        header_id = block.get("id")
                        
                        # Get transactions in this block
                        tx_response = self.session.get(f"{self.api_url}/blocks/header/{header_id}/transactions")
                        if tx_response.status_code == 200:
                            txs = tx_response.json()
                            
                            # Look for transactions with tokens
                            for tx in txs:
                                tx_id = tx.get("id")
                                tx_detail_response = self.session.get(f"{self.api_url}/transactions/{tx_id}")
                                
                                if tx_detail_response.status_code == 200:
                                    tx_detail = tx_detail_response.json()
                                    outputs = tx_detail.get("outputs", [])
                                    
                                    for output in outputs:
                                        assets = output.get("assets", [])
                                        if assets and len(assets) > 0:
                                            return output.get("address")
        except Exception as e:
            logger.error(f"Error finding address with tokens: {str(e)}")
        
        # Fallback: try some known addresses that typically have tokens
        for address in known_addresses:
            try:
                response = self.session.get(f"{self.api_url}/tokens/address/{address}")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("tokens") and len(data.get("tokens", [])) > 0:
                        return address
            except Exception:
                continue
        
        return None
    
    def _get_token_id(self) -> Optional[str]:
        """Find a token ID to test with."""
        logger.info("Looking for a token ID to test...")
        
        # Try to get from top tokens
        try:
            response = self.session.get(f"{self.api_url}/tokens/top")
            if response.status_code == 200:
                data = response.json()
                tokens = data.get("tokens", [])
                if tokens and len(tokens) > 0:
                    return tokens[0].get("tokenId")
        except Exception as e:
            logger.error(f"Error getting token ID from top tokens: {str(e)}")
        
        # Try some known token IDs
        known_tokens = [
            "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",  # SigUSD
            "d71693c49a84fbbecd4908c94813b46514b18b67a99952dc1e6e4791556de413"   # ErgoMixer Token
        ]
        
        for token_id in known_tokens:
            try:
                response = self.session.get(f"{self.api_url}/tokens/{token_id}/holders")
                if response.status_code == 200:
                    return token_id
            except Exception:
                continue
        
        return None
    
    def _test_address_tokens(self, address: str) -> None:
        """
        Test the /tokens/address/{address} endpoint.
        
        Args:
            address: The address to test with
        """
        logger.info(f"Testing address tokens endpoint for address: {address}")
        
        # Test basic functionality
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/address/{address}")
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                assert "address" in data, "Response missing 'address' field"
                assert "tokens" in data, "Response missing 'tokens' field"
                assert "total" in data, "Response missing 'total' field"
                assert "limit" in data, "Response missing 'limit' field"
                assert "offset" in data, "Response missing 'offset' field"
                
                # Validate address matches
                assert data["address"] == address, f"Response address {data['address']} doesn't match requested address {address}"
                
                # Validate tokens array
                tokens = data["tokens"]
                assert isinstance(tokens, list), "Tokens field is not an array"
                
                if len(tokens) > 0:
                    # Validate token structure
                    token = tokens[0]
                    assert "tokenId" in token, "Token missing 'tokenId' field"
                    assert "balance" in token, "Token missing 'balance' field"
                
                logger.info(f"Found {len(tokens)} tokens for address {address}")
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing address tokens: {str(e)}")
            self.failed_tests += 1
        
        # Test pagination
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/address/{address}?limit=5&offset=0")
            if response.status_code == 200:
                data = response.json()
                
                # Validate pagination parameters
                assert data["limit"] == 5, f"Limit parameter not applied correctly, got {data['limit']}, expected 5"
                assert data["offset"] == 0, f"Offset parameter not applied correctly, got {data['offset']}, expected 0"
                
                # Check that tokens are limited correctly
                tokens = data["tokens"]
                assert len(tokens) <= 5, f"Response contains {len(tokens)} tokens, expected ≤ 5"
                
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing address tokens pagination: {str(e)}")
            self.failed_tests += 1
    
    def _test_token_holders(self, token_id: str) -> None:
        """
        Test the /tokens/{tokenId}/holders endpoint.
        
        Args:
            token_id: The token ID to test with
        """
        logger.info(f"Testing token holders endpoint for token: {token_id}")
        
        # Test basic functionality
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/{token_id}/holders")
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                assert "token" in data, "Response missing 'token' field"
                assert "holders" in data, "Response missing 'holders' field"
                assert "total" in data, "Response missing 'total' field"
                assert "limit" in data, "Response missing 'limit' field"
                assert "offset" in data, "Response missing 'offset' field"
                
                # Validate token information
                token = data["token"]
                assert "tokenId" in token, "Token missing 'tokenId' field"
                assert token["tokenId"] == token_id, f"Response token ID {token['tokenId']} doesn't match requested token ID {token_id}"
                
                # Validate holders array
                holders = data["holders"]
                assert isinstance(holders, list), "Holders field is not an array"
                
                if len(holders) > 0:
                    # Validate holder structure
                    holder = holders[0]
                    assert "address" in holder, "Holder missing 'address' field"
                    assert "balance" in holder, "Holder missing 'balance' field"
                    assert "percentage" in holder, "Holder missing 'percentage' field"
                
                logger.info(f"Found {len(holders)} holders for token {token_id}")
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing token holders: {str(e)}")
            self.failed_tests += 1
        
        # Test pagination
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/{token_id}/holders?limit=5&offset=0")
            if response.status_code == 200:
                data = response.json()
                
                # Validate pagination parameters
                assert data["limit"] == 5, f"Limit parameter not applied correctly, got {data['limit']}, expected 5"
                assert data["offset"] == 0, f"Offset parameter not applied correctly, got {data['offset']}, expected 0"
                
                # Check that holders are limited correctly
                holders = data["holders"]
                assert len(holders) <= 5, f"Response contains {len(holders)} holders, expected ≤ 5"
                
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing token holders pagination: {str(e)}")
            self.failed_tests += 1
    
    def _test_top_tokens(self) -> None:
        """Test the /tokens/top endpoint."""
        logger.info("Testing top tokens endpoint")
        
        # Test basic functionality
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/top")
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                assert "tokens" in data, "Response missing 'tokens' field"
                assert "total" in data, "Response missing 'total' field"
                assert "limit" in data, "Response missing 'limit' field"
                assert "offset" in data, "Response missing 'offset' field"
                
                # Validate tokens array
                tokens = data["tokens"]
                assert isinstance(tokens, list), "Tokens field is not an array"
                
                if len(tokens) > 0:
                    # Validate token structure
                    token = tokens[0]
                    assert "tokenId" in token, "Token missing 'tokenId' field"
                    assert "holderCount" in token, "Token missing 'holderCount' field"
                
                logger.info(f"Found {len(tokens)} top tokens")
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing top tokens: {str(e)}")
            self.failed_tests += 1
        
        # Test pagination
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/top?limit=5&offset=0")
            if response.status_code == 200:
                data = response.json()
                
                # Validate pagination parameters
                assert data["limit"] == 5, f"Limit parameter not applied correctly, got {data['limit']}, expected 5"
                assert data["offset"] == 0, f"Offset parameter not applied correctly, got {data['offset']}, expected 0"
                
                # Check that tokens are limited correctly
                tokens = data["tokens"]
                assert len(tokens) <= 5, f"Response contains {len(tokens)} tokens, expected ≤ 5"
                
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing top tokens pagination: {str(e)}")
            self.failed_tests += 1
    
    def _test_edge_cases(self) -> None:
        """Test edge cases and error handling."""
        logger.info("Testing edge cases")
        
        # Test invalid token ID
        self.total_tests += 1
        try:
            invalid_token_id = "0000000000000000000000000000000000000000000000000000000000000000"
            response = self.session.get(f"{self.api_url}/tokens/{invalid_token_id}/holders")
            
            # Should return 404
            if response.status_code == 404:
                logger.info("Invalid token ID test passed - returned 404 as expected")
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code} for invalid token ID, expected 404")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing invalid token ID: {str(e)}")
            self.failed_tests += 1
        
        # Test invalid address
        self.total_tests += 1
        try:
            invalid_address = "invalid_address"
            response = self.session.get(f"{self.api_url}/tokens/address/{invalid_address}")
            
            # Should return 400 or 404
            if response.status_code in [400, 404]:
                logger.info(f"Invalid address test passed - returned {response.status_code} as expected")
                self.passed_tests += 1
            else:
                logger.error(f"API returned status {response.status_code} for invalid address, expected 400 or 404")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing invalid address: {str(e)}")
            self.failed_tests += 1
        
        # Test excessive pagination
        self.total_tests += 1
        try:
            response = self.session.get(f"{self.api_url}/tokens/top?limit=1000&offset=0")
            
            # Should either truncate to max limit or return 400
            if response.status_code == 200:
                data = response.json()
                if data.get("limit", 1000) < 1000:
                    logger.info(f"Excessive limit test passed - limit was truncated to {data['limit']}")
                    self.passed_tests += 1
                else:
                    logger.warning(f"Excessive limit allowed: {data['limit']}")
                    self.failed_tests += 1
            elif response.status_code == 400:
                logger.info("Excessive limit test passed - returned 400 as expected")
                self.passed_tests += 1
            else:
                logger.error(f"API returned unexpected status {response.status_code} for excessive limit")
                self.failed_tests += 1
        except Exception as e:
            logger.error(f"Error testing excessive pagination: {str(e)}")
            self.failed_tests += 1


def main():
    """Main function to run the token API validation."""
    parser = argparse.ArgumentParser(description="Token API Validation Script")
    parser.add_argument("--api-url", required=True, help="URL of the Shark Explorer API")
    parser.add_argument("--node-url", help="Optional URL of the Ergo node for comparison")
    parser.add_argument("--output", help="Output file for JSON results")
    
    args = parser.parse_args()
    
    validator = TokenAPIValidator(args.api_url, args.node_url)
    success = validator.run_all_tests()
    
    if args.output:
        results = {
            "timestamp": datetime.now().isoformat(),
            "api_url": args.api_url,
            "total_tests": validator.total_tests,
            "passed_tests": validator.passed_tests,
            "failed_tests": validator.failed_tests,
            "success_rate": (validator.passed_tests / validator.total_tests) * 100 if validator.total_tests > 0 else 0,
            "success": success
        }
        
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 