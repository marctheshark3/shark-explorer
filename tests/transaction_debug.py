#!/usr/bin/env python3
"""
Transaction API debugging script for Ergo Explorer API.
This script helps diagnose issues with the transaction API endpoints.
"""

import requests
import json
import sys
import time
import argparse
import traceback
import logging
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("transaction_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TransactionDebugger:
    def __init__(self, api_base_url: str, node_url: Optional[str] = None):
        """
        Initialize the transaction debugger.
        
        Args:
            api_base_url: Base URL for the Ergo Explorer API
            node_url: Optional Ergo node URL for comparison
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.node_url = node_url
        if node_url:
            self.node_url = node_url.rstrip("/")
    
    def find_transaction_in_recent_blocks(self, n_blocks: int = 10) -> Optional[str]:
        """
        Find a transaction ID in recent blocks.
        
        Args:
            n_blocks: Number of recent blocks to check
            
        Returns:
            Transaction ID if found, None otherwise
        """
        try:
            # Get current block height
            logger.info(f"Getting current block height from API...")
            height_response = requests.get(f"{self.api_base_url}/blocks/count")
            height_response.raise_for_status()
            current_height = height_response.json()
            logger.info(f"Current block height: {current_height}")
            
            # Get recent blocks
            start_height = max(1, current_height - n_blocks + 1)
            logger.info(f"Getting blocks from heights {start_height} to {current_height}...")
            blocks_response = requests.get(f"{self.api_base_url}/blocks/range/{start_height}/{current_height}")
            blocks_response.raise_for_status()
            blocks = blocks_response.json()
            
            # Find a block with transactions
            for block in blocks:
                if block.get("transactionsCount", 0) > 0:
                    block_hash = block["hash"]
                    block_height = block["height"]
                    logger.info(f"Found block with transactions: height={block_height}, hash={block_hash}")
                    
                    # Get transactions for this block
                    logger.info(f"Getting transactions for block {block_hash}...")
                    tx_response = requests.get(f"{self.api_base_url}/blocks/{block_hash}/transactions")
                    tx_response.raise_for_status()
                    transactions = tx_response.json()
                    
                    if transactions and len(transactions) > 0:
                        tx_id = transactions[0]["id"]
                        logger.info(f"Found transaction ID: {tx_id}")
                        return tx_id
            
            logger.warning("No transactions found in recent blocks")
            return None
            
        except Exception as e:
            logger.error(f"Error finding transaction in recent blocks: {e}")
            traceback.print_exc()
            return None
    
    def get_transaction_from_api(self, tx_id: str) -> Dict:
        """
        Get transaction details from the API.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Transaction details or error information
        """
        result = {
            "tx_id": tx_id,
            "api_url": f"{self.api_base_url}/transactions/{tx_id}",
            "status_code": None,
            "response_time_ms": None,
            "error": None,
            "data": None
        }
        
        try:
            logger.info(f"Getting transaction {tx_id} from API...")
            start_time = time.time()
            response = requests.get(f"{self.api_base_url}/transactions/{tx_id}")
            end_time = time.time()
            
            result["status_code"] = response.status_code
            result["response_time_ms"] = int((end_time - start_time) * 1000)
            
            logger.info(f"API response status code: {response.status_code}")
            logger.info(f"API response time: {result['response_time_ms']} ms")
            
            if response.status_code == 200:
                result["data"] = response.json()
                logger.info("Successfully retrieved transaction from API")
            else:
                result["error"] = response.text
                logger.error(f"API error: {response.text}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Exception when calling API: {e}")
            traceback.print_exc()
        
        return result
    
    def get_transaction_from_node(self, tx_id: str) -> Dict:
        """
        Get transaction details from the Ergo node if available.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Transaction details or error information
        """
        if not self.node_url:
            return {"error": "Node URL not provided"}
        
        result = {
            "tx_id": tx_id,
            "node_url": f"{self.node_url}/transactions/{tx_id}",
            "status_code": None,
            "response_time_ms": None,
            "error": None,
            "data": None
        }
        
        try:
            logger.info(f"Getting transaction {tx_id} from node...")
            start_time = time.time()
            response = requests.get(f"{self.node_url}/transactions/{tx_id}")
            end_time = time.time()
            
            result["status_code"] = response.status_code
            result["response_time_ms"] = int((end_time - start_time) * 1000)
            
            logger.info(f"Node response status code: {response.status_code}")
            logger.info(f"Node response time: {result['response_time_ms']} ms")
            
            if response.status_code == 200:
                result["data"] = response.json()
                logger.info("Successfully retrieved transaction from node")
            else:
                result["error"] = response.text
                logger.error(f"Node error: {response.text}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Exception when calling node: {e}")
            traceback.print_exc()
        
        return result
    
    def compare_transactions(self, api_data: Dict, node_data: Dict) -> Dict:
        """
        Compare transaction data from API and node.
        
        Args:
            api_data: Transaction data from API
            node_data: Transaction data from node
            
        Returns:
            Dictionary with comparison results
        """
        if api_data.get("error") or node_data.get("error"):
            return {
                "can_compare": False,
                "api_error": api_data.get("error"),
                "node_error": node_data.get("error")
            }
        
        result = {
            "can_compare": True,
            "differences": {}
        }
        
        # Compare basic fields
        if api_data["data"]["id"] != node_data["data"]["id"]:
            result["differences"]["id"] = {
                "api": api_data["data"]["id"],
                "node": node_data["data"]["id"]
            }
        
        # TODO: Add more detailed comparison as needed
        
        return result
    
    def check_api_database_connection(self) -> Dict:
        """
        Check the API's database connection.
        
        Returns:
            Dictionary with connection status
        """
        result = {
            "status": None,
            "error": None,
            "health_endpoint_available": False
        }
        
        try:
            logger.info("Checking API health endpoint...")
            response = requests.get(f"{self.api_base_url}/health")
            result["health_endpoint_available"] = response.status_code == 200
            
            if response.status_code == 200:
                result["status"] = "healthy"
                logger.info("API health endpoint reports healthy")
            else:
                result["status"] = "unhealthy"
                result["error"] = response.text
                logger.warning(f"API health endpoint reports unhealthy: {response.text}")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Error checking API health: {e}")
            traceback.print_exc()
        
        return result
    
    def debug_transaction(self, tx_id: Optional[str] = None) -> Dict:
        """
        Debug a transaction API issue.
        
        Args:
            tx_id: Transaction ID to debug (optional)
            
        Returns:
            Dictionary with debug information
        """
        result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tx_id": tx_id,
            "api_url": self.api_base_url,
            "node_url": self.node_url,
            "api_health": None,
            "api_result": None,
            "node_result": None,
            "comparison": None
        }
        
        try:
            # Check API health
            result["api_health"] = self.check_api_database_connection()
            
            # Find a transaction if none provided
            if not tx_id:
                tx_id = self.find_transaction_in_recent_blocks()
                result["tx_id"] = tx_id
            
            if not tx_id:
                logger.error("No transaction ID provided or found")
                return result
            
            # Get transaction from API
            result["api_result"] = self.get_transaction_from_api(tx_id)
            
            # Get transaction from node if available
            if self.node_url:
                result["node_result"] = self.get_transaction_from_node(tx_id)
                
                # Compare results if both available
                if (result["api_result"].get("data") and 
                    result["node_result"].get("data")):
                    result["comparison"] = self.compare_transactions(
                        result["api_result"], 
                        result["node_result"]
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Error during transaction debugging: {e}")
            traceback.print_exc()
            result["error"] = str(e)
            return result

def main():
    parser = argparse.ArgumentParser(description="Debug Ergo Explorer API transaction endpoints")
    parser.add_argument("--api-url", default="http://localhost:8082", help="Base URL for the Ergo Explorer API")
    parser.add_argument("--node-url", help="Ergo node URL for comparison (optional)")
    parser.add_argument("--tx-id", help="Transaction ID to check (optional)")
    parser.add_argument("--output", help="Output file for debug results (JSON)")
    args = parser.parse_args()
    
    logger.info(f"Starting transaction debugger with API URL: {args.api_url}")
    if args.node_url:
        logger.info(f"Using node URL for comparison: {args.node_url}")
    
    debugger = TransactionDebugger(args.api_url, args.node_url)
    result = debugger.debug_transaction(args.tx_id)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Debug results written to {args.output}")
    else:
        print(json.dumps(result, indent=2))
    
    # Report success or failure
    if result.get("api_result") and result["api_result"].get("status_code") == 200:
        logger.info("Transaction API is working correctly")
        sys.exit(0)
    else:
        logger.error("Transaction API has issues")
        sys.exit(1)

if __name__ == "__main__":
    main() 