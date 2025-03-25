#!/usr/bin/env python3
"""
API validation script for Ergo Explorer API.
Tests various endpoints to ensure they are functioning correctly.
"""

import requests
import json
import sys
import time
import argparse
from typing import Dict, List, Optional, Any, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class ErgoAPIValidator:
    def __init__(self, api_base_url: str, node_url: Optional[str] = None):
        """
        Initialize the validator with API and node URLs.
        
        Args:
            api_base_url: Base URL for the Ergo Explorer API
            node_url: Optional Ergo node URL for comparison
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.node_url = node_url
        if node_url:
            self.node_url = node_url.rstrip("/")
        self.failed_tests = []
        self.successful_tests = []

    def run_test(self, name: str, func, *args, **kwargs) -> bool:
        """
        Run a test function and log the result.
        
        Args:
            name: Name of the test
            func: Test function to run
            args, kwargs: Arguments to pass to the test function
            
        Returns:
            True if test passed, False otherwise
        """
        logger.info(f"Running test: {name}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"✅ Test passed: {name}")
            self.successful_tests.append(name)
            return True
        except Exception as e:
            logger.error(f"❌ Test failed: {name}")
            logger.error(f"Error: {str(e)}")
            self.failed_tests.append((name, str(e)))
            return False

    def get_blocks_count(self) -> Tuple[int, int]:
        """
        Get the count of blocks from both API and node.
        
        Returns:
            Tuple of (api_count, node_count)
        """
        api_response = requests.get(f"{self.api_base_url}/blocks/count")
        api_response.raise_for_status()
        api_count = api_response.json()
        
        if self.node_url:
            node_response = requests.get(f"{self.node_url}/info")
            node_response.raise_for_status()
            node_count = node_response.json()["fullHeight"]
        else:
            node_count = None
            
        return api_count, node_count

    def test_health(self) -> None:
        """Test the health endpoint"""
        response = requests.get(f"{self.api_base_url}/health")
        response.raise_for_status()
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"

    def test_get_block_by_height(self, height: int) -> None:
        """Test getting a block by height"""
        response = requests.get(f"{self.api_base_url}/blocks/at/{height}")
        response.raise_for_status()
        block = response.json()
        assert block["height"] == height, f"Block height mismatch: {block['height']} != {height}"
        logger.info(f"Block at height {height}: {block['hash']}")
        
        # Also check with node if available
        if self.node_url:
            node_response = requests.get(f"{self.node_url}/blocks/at/{height}")
            node_response.raise_for_status()
            node_block = node_response.json()
            assert block["hash"] == node_block["header"]["id"], "Block hash mismatch between API and node"

    def test_get_latest_blocks(self, limit: int = 10) -> None:
        """Test getting the latest blocks"""
        response = requests.get(f"{self.api_base_url}/blocks/latest?limit={limit}")
        response.raise_for_status()
        blocks = response.json()
        assert len(blocks) <= limit, f"Expected at most {limit} blocks, got {len(blocks)}"
        
        # Check if blocks are in descending order by height
        heights = [block["height"] for block in blocks]
        assert all(heights[i] > heights[i+1] for i in range(len(heights)-1)), "Blocks not in descending order"

    def test_get_transaction(self, tx_id: str) -> None:
        """Test getting a transaction by ID"""
        response = requests.get(f"{self.api_base_url}/transactions/{tx_id}")
        if response.status_code != 200:
            logger.warning(f"Transaction endpoint returned {response.status_code}: {response.text}")
        response.raise_for_status()
        tx = response.json()
        assert tx["id"] == tx_id, f"Transaction ID mismatch: {tx['id']} != {tx_id}"
        
        # Also check with node if available
        if self.node_url:
            node_response = requests.get(f"{self.node_url}/transactions/{tx_id}")
            node_response.raise_for_status()
            node_tx = node_response.json()
            assert tx["id"] == node_tx["id"], "Transaction ID mismatch between API and node"

    def test_search_by_transaction(self, tx_id: str) -> None:
        """Test searching by transaction ID"""
        response = requests.get(f"{self.api_base_url}/search/transaction/{tx_id}")
        response.raise_for_status()
        result = response.json()
        assert result is not None, "Search result should not be None"

    def test_address_transactions(self, address: str, limit: int = 10) -> None:
        """Test getting transactions for an address"""
        response = requests.get(f"{self.api_base_url}/addresses/{address}/transactions?limit={limit}")
        response.raise_for_status()
        txs = response.json()
        assert isinstance(txs, list), "Expected a list of transactions"
        assert len(txs) <= limit, f"Expected at most {limit} transactions, got {len(txs)}"
        
    def test_address_balance(self, address: str) -> None:
        """Test getting address balance"""
        response = requests.get(f"{self.api_base_url}/addresses/{address}/balance")
        response.raise_for_status()
        balance = response.json()
        assert "confirmed" in balance, "Balance response missing 'confirmed' field"
        assert isinstance(balance["confirmed"]["nanoErgs"], int), "NanoErgs should be an integer"

    def test_token_info(self, token_id: str) -> None:
        """Test getting token information"""
        response = requests.get(f"{self.api_base_url}/tokens/{token_id}")
        response.raise_for_status()
        token = response.json()
        assert token["id"] == token_id, f"Token ID mismatch: {token['id']} != {token_id}"

    def test_blocks_range(self, min_height: int, max_height: int) -> None:
        """Test getting blocks within a height range"""
        response = requests.get(f"{self.api_base_url}/blocks/range/{min_height}/{max_height}")
        response.raise_for_status()
        blocks = response.json()
        assert len(blocks) == (max_height - min_height + 1), f"Expected {max_height - min_height + 1} blocks, got {len(blocks)}"
        
        # Check if all blocks have heights within the specified range
        for block in blocks:
            assert min_height <= block["height"] <= max_height, f"Block height {block['height']} outside of range {min_height}-{max_height}"

    def find_transaction_in_last_n_blocks(self, n: int = 10) -> Optional[str]:
        """Find a transaction ID in the last N blocks to use for testing"""
        logger.info(f"Looking for a transaction in the last {n} blocks...")
        api_count, _ = self.get_blocks_count()
        
        # Get the latest N blocks
        latest_height = api_count
        min_height = max(1, latest_height - n + 1)
        
        response = requests.get(f"{self.api_base_url}/blocks/range/{min_height}/{latest_height}")
        response.raise_for_status()
        blocks = response.json()
        
        # Find a block with transactions
        for block in blocks:
            if block.get("transactionsCount", 0) > 0:
                # Get transactions for this block
                block_response = requests.get(f"{self.api_base_url}/blocks/{block['hash']}/transactions")
                block_response.raise_for_status()
                transactions = block_response.json()
                
                if transactions and len(transactions) > 0:
                    tx_id = transactions[0]["id"]
                    logger.info(f"Found transaction {tx_id} in block {block['height']}")
                    return tx_id
        
        logger.warning("Could not find any transactions in the last N blocks")
        return None

    def find_address_with_transactions(self, n: int = 10) -> Optional[str]:
        """Find an address with transactions in the last N blocks"""
        tx_id = self.find_transaction_in_last_n_blocks(n)
        if not tx_id:
            return None
            
        response = requests.get(f"{self.api_base_url}/transactions/{tx_id}")
        response.raise_for_status()
        tx = response.json()
        
        # Extract an address from the transaction outputs
        if tx.get("outputs") and len(tx["outputs"]) > 0:
            address = tx["outputs"][0].get("address")
            if address:
                logger.info(f"Found address {address} with transactions")
                return address
        
        logger.warning("Could not find an address with transactions")
        return None

    def find_token_id(self, n: int = 50) -> Optional[str]:
        """Find a token ID in the last N blocks"""
        logger.info(f"Looking for a token in the last {n} blocks...")
        api_count, _ = self.get_blocks_count()
        
        # Get the latest N blocks
        latest_height = api_count
        min_height = max(1, latest_height - n + 1)
        
        response = requests.get(f"{self.api_base_url}/blocks/range/{min_height}/{latest_height}")
        response.raise_for_status()
        blocks = response.json()
        
        # Find a block with transactions
        for block in blocks:
            block_response = requests.get(f"{self.api_base_url}/blocks/{block['hash']}/transactions")
            block_response.raise_for_status()
            transactions = block_response.json()
            
            for tx in transactions:
                if tx.get("outputs"):
                    for output in tx["outputs"]:
                        if output.get("assets") and len(output["assets"]) > 0:
                            token_id = output["assets"][0]["tokenId"]
                            logger.info(f"Found token {token_id}")
                            return token_id
        
        logger.warning("Could not find any tokens in the last N blocks")
        return None

    def run_all_tests(self) -> None:
        """Run all validation tests"""
        logger.info("Starting API validation tests")
        
        # Basic health check
        self.run_test("Health check", self.test_health)
        
        # Get block count to use in other tests
        api_count, node_count = self.get_blocks_count()
        logger.info(f"Block count from API: {api_count}")
        if node_count:
            logger.info(f"Block count from node: {node_count}")
            logger.info(f"Indexing progress: {api_count/node_count*100:.2f}%")
        
        # Test block endpoints with a block in the middle of the indexed range
        test_height = api_count // 2
        self.run_test(f"Get block at height {test_height}", self.test_get_block_by_height, test_height)
        
        # Test getting latest blocks
        self.run_test("Get latest blocks", self.test_get_latest_blocks)
        
        # Test blocks range
        min_height = max(1, api_count - 10)
        max_height = api_count
        self.run_test(f"Get blocks range {min_height}-{max_height}", self.test_blocks_range, min_height, max_height)
        
        # Find a transaction to test with
        tx_id = self.find_transaction_in_last_n_blocks()
        if tx_id:
            self.run_test(f"Get transaction {tx_id}", self.test_get_transaction, tx_id)
            self.run_test(f"Search by transaction {tx_id}", self.test_search_by_transaction, tx_id)
        
        # Find an address to test with
        address = self.find_address_with_transactions()
        if address:
            self.run_test(f"Get address transactions for {address}", self.test_address_transactions, address)
            self.run_test(f"Get address balance for {address}", self.test_address_balance, address)
        
        # Find a token to test with
        token_id = self.find_token_id()
        if token_id:
            self.run_test(f"Get token info for {token_id}", self.test_token_info, token_id)
        
        # Print summary
        logger.info("\n===== TEST SUMMARY =====")
        logger.info(f"Total tests: {len(self.successful_tests) + len(self.failed_tests)}")
        logger.info(f"Successful tests: {len(self.successful_tests)}")
        logger.info(f"Failed tests: {len(self.failed_tests)}")
        
        if self.failed_tests:
            logger.error("\nFailed tests:")
            for name, error in self.failed_tests:
                logger.error(f" - {name}: {error}")
            sys.exit(1)
        else:
            logger.info("\nAll tests passed successfully!")

def main():
    parser = argparse.ArgumentParser(description="Validate Ergo Explorer API endpoints")
    parser.add_argument("--api-url", default="http://localhost:8082", help="Base URL for the Ergo Explorer API")
    parser.add_argument("--node-url", help="Ergo node URL for comparison (optional)")
    args = parser.parse_args()
    
    validator = ErgoAPIValidator(args.api_url, args.node_url)
    validator.run_all_tests()

if __name__ == "__main__":
    main() 