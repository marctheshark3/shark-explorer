import os
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple, Union
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import registry
from concurrent.futures import ThreadPoolExecutor

from ..db.models import Block, Transaction, Input, Output, Asset, SyncStatus, MiningReward, AddressStats, TokenInfo, AssetMetadata, mapper_registry
from ..db.database import get_session, bulk_insert_mappings, batch_operation_context, multi_block_transaction
from ..utils.performance import timed, performance_tracker, Timer
from ..utils.redis_client import redis_client
from .node import NodeClient

logger = structlog.get_logger()

class IndexerService:
    def __init__(self, node_client: NodeClient, config: Optional[Dict[str, Any]] = None):
        self.node = node_client
        self.is_running = False
        self.current_height = 0
        self.target_height = 0
        
        # Default configuration
        self.config = {
            'batch_size': int(os.getenv('INDEXER_BATCH_SIZE', '20')),  # Number of blocks to process in parallel
            'max_workers': int(os.getenv('INDEXER_MAX_WORKERS', '5')),  # Max number of worker tasks
            'bulk_insert': os.getenv('INDEXER_BULK_INSERT', 'True').lower() == 'true',  # Use bulk inserts
            'use_redis_cache': os.getenv('INDEXER_USE_REDIS', 'True').lower() == 'true',  # Use Redis caching
            'process_tokens': os.getenv('INDEXER_PROCESS_TOKENS', 'True').lower() == 'true',  # Process token metadata
            'parallel_mode': os.getenv('INDEXER_PARALLEL_MODE', 'True').lower() == 'true',  # Enable parallel processing
        }
        
        # Override with provided config
        if config:
            self.config.update(config)
            
        # Statistics
        self.stats = {
            'blocks_processed': 0,
            'transactions_processed': 0,
            'inputs_processed': 0,
            'outputs_processed': 0,
            'assets_processed': 0,
            'start_time': 0,
            'processing_time': 0,
            'errors': 0,
        }

    async def start(self):
        """Start the indexer service."""
        if self.is_running:
            return

        self.is_running = True
        self.stats['start_time'] = time.time()
        try:
            await self._run_indexer()
        finally:
            self.is_running = False
            self.stats['processing_time'] = time.time() - self.stats['start_time']
            logger.info(
                "Indexer stopped",
                blocks_processed=self.stats['blocks_processed'],
                transactions=self.stats['transactions_processed'],
                errors=self.stats['errors'],
                processing_time=f"{self.stats['processing_time']:.2f}s"
            )

    async def stop(self):
        """Stop the indexer service."""
        self.is_running = False

    @timed("indexer_run")
    async def _run_indexer(self):
        """Main indexer loop."""
        while self.is_running:
            try:
                # Update sync status
                await self._update_sync_status()

                # Check if we're caught up
                if self.current_height >= self.target_height:
                    logger.info("Indexer is caught up", height=self.current_height)
                    await asyncio.sleep(10)
                    continue

                # Determine how many blocks to process in this batch
                remaining_blocks = self.target_height - self.current_height
                
                # Dynamically adjust batch size based on remaining blocks
                # Process larger batches when far behind, smaller batches when almost caught up
                dynamic_batch_size = min(
                    self.config['batch_size'],
                    max(10, min(remaining_blocks, self.config['batch_size'] * 2 if remaining_blocks > 1000 else self.config['batch_size']))
                )
                
                blocks_to_process = min(dynamic_batch_size, remaining_blocks)
                
                logger.info(
                    "Starting indexing batch", 
                    current_height=self.current_height,
                    target_height=self.target_height,
                    remaining=remaining_blocks,
                    batch_size=blocks_to_process
                )
                
                # Process blocks in batch
                if self.config['parallel_mode'] and blocks_to_process > 1:
                    batch_start_time = time.time()
                    
                    await self._process_height_range(
                        self.current_height + 1, 
                        self.current_height + blocks_to_process
                    )
                    
                    batch_time = time.time() - batch_start_time
                    blocks_per_second = blocks_to_process / max(0.1, batch_time)
                    
                    self.current_height += blocks_to_process
                    self.stats['blocks_processed'] += blocks_to_process
                else:
                    # Traditional sequential processing for single blocks
                    await self._process_height(self.current_height + 1)
                    self.current_height += 1
                    blocks_per_second = 1  # Just processed one block

                # Record metrics and log progress
                total_blocks_per_second = self.stats['blocks_processed'] / max(1, time.time() - self.stats['start_time'])
                logger.info(
                    "Indexing progress", 
                    height=self.current_height,
                    target=self.target_height,
                    remaining=self.target_height - self.current_height,
                    last_batch_blocks_per_second=f"{blocks_per_second:.2f}",
                    overall_blocks_per_second=f"{total_blocks_per_second:.2f}"
                )

            except Exception as e:
                self.stats['errors'] += 1
                logger.error("Error in indexer loop", error=str(e), exc_info=True)
                await asyncio.sleep(5)

    @timed("sync_status_update")
    async def _update_sync_status(self):
        """Update sync status from node and database."""
        try:
            # Note: SQLAlchemy registry is configured in __main__.py
            
            node_height = await self.node.get_current_height()
            self.target_height = node_height

            async with get_session() as session:
                status = await self._get_or_create_sync_status(session)
                self.current_height = status.current_height
                
                # Update status
                status.target_height = node_height
                status.is_syncing = self.is_running
                status.last_block_time = int(datetime.utcnow().timestamp())
                await session.commit()

        except Exception as e:
            logger.error("Error updating sync status", error=str(e), exc_info=True)
            raise

    async def _get_or_create_sync_status(self, session: AsyncSession) -> SyncStatus:
        """Get or create sync status record."""
        result = await session.execute(select(SyncStatus).where(SyncStatus.id == 1))
        status = result.scalar_one_or_none()

        if not status:
            status = SyncStatus(
                id=1,
                current_height=0,
                target_height=0,
                is_syncing=False
            )
            session.add(status)
            await session.commit()

        return status

    def _validate_block_data(self, block_data: Dict[str, Any]) -> None:
        """Validate block data structure."""
        required_fields = ['header', 'blockTransactions', 'height']
        for field in required_fields:
            if field not in block_data:
                raise ValueError(f"Missing required field '{field}' in block data")
                
        header = block_data['header']
        required_header_fields = ['id', 'timestamp', 'parentId', 'difficulty', 'version']
        for field in required_header_fields:
            if field not in header:
                raise ValueError(f"Missing required field '{field}' in block header")
        
        # Add block ID from header to root level for consistency
        block_data['id'] = header['id']

    def _validate_transaction_data(self, tx_data: Dict[str, Any]) -> None:
        """Validate transaction data structure."""
        required_fields = ['id', 'inputs', 'outputs']
        for field in required_fields:
            if field not in tx_data:
                raise ValueError(f"Missing required field '{field}' in transaction data")

    @timed("process_height_range")
    async def _process_height_range(self, start_height: int, end_height: int):
        """Process a range of block heights in parallel using a producer-consumer pattern."""
        if start_height > end_height:
            logger.warning("Start height greater than end height", start=start_height, end=end_height)
            return

        # Check if we need to process blocks sequentially first to maintain referential integrity
        sequential_steps = self.config.get('sequential_steps', 20)
        current_height = start_height
        
        # First, process a small batch of blocks sequentially to establish chain integrity
        if sequential_steps > 0 and (end_height - start_height) > 1:
            seq_end_height = min(start_height + sequential_steps - 1, end_height)
            logger.info({
                "event": "Processing initial blocks sequentially to maintain referential integrity",
                "start_height": start_height,
                "end_height": seq_end_height
            })
            
            # Process blocks sequentially
            for height in range(start_height, seq_end_height + 1):
                await self._process_height(height)
            
            # Update current height for parallel processing
            current_height = seq_end_height + 1
            
            # If we've processed all blocks sequentially, we're done
            if current_height > end_height:
                logger.info(f"Completed processing block range sequentially", 
                           start=start_height, end=end_height)
                # Update the current height in the database
                async with get_session() as session:
                    status = await self._get_or_create_sync_status(session)
                    status.current_height = end_height
                    await session.commit()
                return
        
        # For remaining blocks, use parallel processing with queues
        logger.info(f"Processing remaining blocks in parallel", 
                   start=current_height, end=end_height)
        
        # Create a queue for blocks to be processed
        block_queue = asyncio.Queue(maxsize=self.config['batch_size'] * 2)
        
        # Create a semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.config['max_workers'])
        
        # Start the producer task to fetch blocks
        producer_task = asyncio.create_task(self._block_producer(block_queue, current_height, end_height))
        
        # Start consumer workers
        consumer_tasks = [
            asyncio.create_task(self._block_consumer(block_queue, semaphore))
            for _ in range(self.config['max_workers'])
        ]
        
        # Wait for the producer to finish
        await producer_task
        
        # Signal consumers to stop by adding None to the queue
        for _ in range(len(consumer_tasks)):
            await block_queue.put(None)
        
        # Wait for all consumers to finish
        await asyncio.gather(*consumer_tasks)
        
        # Update the current height in the database
        async with get_session() as session:
            status = await self._get_or_create_sync_status(session)
            status.current_height = end_height
            await session.commit()
        
        logger.info(f"Completed processing block range", start=start_height, end=end_height)

    async def _block_producer(self, queue: asyncio.Queue, start_height: int, end_height: int):
        """Fetch blocks from the node and add them to the queue."""
        try:
            # Use configurable fetch batch size
            fetch_batch_size = self.config.get('fetch_batch_size', 20)
            total_blocks = end_height - start_height + 1
            
            logger.info(
                f"Starting block producer", 
                start=start_height, 
                end=end_height, 
                total=total_blocks,
                fetch_batch_size=fetch_batch_size
            )
            
            current_height = start_height
            blocks_fetched = 0
            fetch_start_time = time.time()
            
            # Use smaller batches for better control over ordering
            # This helps with foreign key constraints by ensuring parent blocks are processed
            # before child blocks in case of any out-of-order processing
            adjusted_batch_size = min(fetch_batch_size, 20)  # Cap batch size for better control
            
            while current_height <= end_height and self.is_running:
                # Calculate batch size for this iteration
                remaining = end_height - current_height + 1
                current_batch_size = min(adjusted_batch_size, remaining)
                batch_end = current_height + current_batch_size - 1
                
                # Create a timer for this batch
                batch_timer = Timer()
                
                # Fetch a batch of blocks in correct height order
                blocks = await self.node.get_blocks_in_range(current_height, batch_end)
                
                # Sort blocks by height to guarantee order
                blocks.sort(key=lambda b: b.get('height', 0))
                
                blocks_fetched += len(blocks)
                
                # Log the fetch performance
                batch_time = batch_timer.elapsed()
                blocks_per_second = len(blocks) / max(0.1, batch_time)
                
                logger.info(
                    "Fetched blocks batch", 
                    start=current_height,
                    end=batch_end,
                    fetched=len(blocks),
                    expected=current_batch_size,
                    time=f"{batch_time:.2f}s",
                    blocks_per_second=f"{blocks_per_second:.2f}",
                    queue_size=queue.qsize(),
                    memory_usage=f"{self.get_memory_usage():.1f}MB"
                )
                    
                # Put each block in the queue in height order
                for block in blocks:
                    if not self.is_running:
                        break
                    await queue.put(block)
                    
                # Update current height
                current_height = batch_end + 1
                
                # Calculate overall progress
                progress_pct = min(100, 100 * (blocks_fetched / total_blocks))
                elapsed = time.time() - fetch_start_time
                blocks_per_second_total = blocks_fetched / max(0.1, elapsed)
                
                # Log overall progress periodically
                if blocks_fetched % (fetch_batch_size * 5) == 0 or current_height > end_height:
                    logger.info(
                        "Block fetching progress", 
                        fetched=blocks_fetched,
                        total=total_blocks,
                        progress=f"{progress_pct:.1f}%",
                        time=f"{elapsed:.1f}s",
                        blocks_per_second=f"{blocks_per_second_total:.2f}",
                        estimated_remaining=f"{(total_blocks - blocks_fetched) / max(1, blocks_per_second_total):.1f}s" if blocks_per_second_total > 0 else "N/A"
                    )
                    
                # Apply backpressure if queue is getting full
                queue_size = queue.qsize()
                if queue_size > self.config.get('batch_size', 20) * 1.5:  # Lower threshold
                    # More aggressive backoff to ensure consumers can catch up
                    wait_time = min(2.0, 0.2 * (queue_size / self.config.get('batch_size', 20)))
                    logger.debug(f"Applying backpressure - queue size: {queue_size}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    
        except Exception as e:
            logger.error("Error in block producer", error=str(e), exc_info=True)
            raise

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0  # psutil not available

    async def _block_consumer(self, queue: asyncio.Queue, semaphore: asyncio.Semaphore):
        """Process blocks from the queue with controlled concurrency and batching."""
        batch = []
        batch_max_size = min(self.config.get('db_batch_size', 10), 5)  # Smaller batches for better error handling
        last_batch_time = time.time()
        
        # Track heights we've seen to detect potential ordering issues
        processed_heights = set()
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        # Get the last processed height from the database to use as reference
        async with get_session() as session:
            status = await self._get_or_create_sync_status(session)
            last_processed_height = status.current_height
        
        while True:
            try:
                # Get block from queue with timeout to allow periodic batch processing
                try:
                    block_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    # Check for termination signal
                    if block_data is None:
                        # Process any remaining blocks in batch before exiting
                        if batch:
                            async with semaphore:
                                await self._process_blocks_batch(batch)
                            batch = []
                        queue.task_done()
                        break
                    
                    # Extract block height for ordering checks
                    block_height = block_data.get('height')
                    
                    # Check for missing parent blocks
                    # If parent blocks are missing, queue might be out of order
                    # This is a heuristic check - not perfect but helpful
                    if block_height > last_processed_height + 1:  # Not the first block
                        # Check if previous height was processed
                        if block_height - 1 not in processed_heights and block_height - 1 > last_processed_height:
                            logger.warning(
                                "Potential block ordering issue detected",
                                height=block_height,
                                missing_parent=block_height - 1,
                                last_processed=last_processed_height
                            )
                            # Handle this block individually to avoid foreign key issues
                            async with semaphore:
                                await self._process_height(block_height)
                            processed_heights.add(block_height)
                            queue.task_done()
                            consecutive_failures = 0
                            continue
                        
                    # Add to current batch
                    batch.append(block_data)
                    queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No block received within timeout, continue to batch processing check
                    pass
                    
                # Process batch if it's full or if enough time has passed
                current_time = time.time()
                batch_timeout = (current_time - last_batch_time) > 5.0  # 5-second timeout
                
                if len(batch) >= batch_max_size or (batch and batch_timeout):
                    logger.debug(f"Processing batch of {len(batch)} blocks (timeout: {batch_timeout})")
                    try:
                        async with semaphore:
                            success = await self._process_blocks_batch(batch)
                        
                        # Add successfully processed heights to our tracking set
                        for block in batch:
                            processed_heights.add(block.get('height'))
                        
                        consecutive_failures = 0
                    except Exception as batch_error:
                        consecutive_failures += 1
                        logger.error(
                            "Batch processing failed",
                            error=str(batch_error),
                            consecutive_failures=consecutive_failures
                        )
                        
                        # If we've had multiple consecutive failures, switch to individual processing
                        if consecutive_failures >= max_consecutive_failures:
                            logger.warning(
                                "Multiple consecutive batch failures detected, switching to individual processing"
                            )
                            # Process each block individually
                            for block in batch:
                                try:
                                    height = block.get('height')
                                    async with semaphore:
                                        await self._process_height(height)
                                    processed_heights.add(height)
                                except Exception as individual_error:
                                    logger.error(
                                        "Individual block processing failed",
                                        height=block.get('height'),
                                        error=str(individual_error)
                                    )
                            # Reset failure counter
                            consecutive_failures = 0
                    
                    # Reset batch and timer
                    batch = []
                    last_batch_time = current_time
                    
            except Exception as e:
                logger.error(
                    "Error in block consumer", 
                    error=str(e), 
                    exc_info=True
                )
                # Don't fail the whole consumer on error
                if batch:
                    logger.warning(f"Discarding batch of {len(batch)} blocks due to error")
                    batch = []
                    last_batch_time = time.time()

    @timed("process_blocks_batch")
    async def _process_blocks_batch(self, blocks: List[Dict[str, Any]]):
        """Process multiple blocks in a single optimized database transaction."""
        if not blocks:
            return
        
        block_count = len(blocks)
        block_heights = [block.get('height', '?') for block in blocks]
        logger.info(
            f"Processing batch of {block_count} blocks", 
            heights=f"{min(block_heights)}-{max(block_heights)}"
        )
        
        # Sort blocks by height to ensure proper order for referential integrity
        blocks.sort(key=lambda b: b.get('height', 0))
        
        # Process blocks in smaller sub-batches to minimize transaction size
        # and maintain referential integrity while still getting some parallelism benefits
        sub_batch_size = min(5, max(1, block_count // 2))
        sub_batches = [blocks[i:i + sub_batch_size] for i in range(0, block_count, sub_batch_size)]
        
        for batch_idx, sub_batch in enumerate(sub_batches):
            logger.debug(f"Processing sub-batch {batch_idx+1}/{len(sub_batches)} with {len(sub_batch)} blocks")
            
            # Use optimized transaction for multiple blocks
            async with multi_block_transaction(block_count=len(sub_batch)) as session:
                try:
                    # Process each block but commit only at the end of the sub-batch
                    for i, block_data in enumerate(sub_batch):
                        try:
                            # Validate block data
                            self._validate_block_data(block_data)
                            
                            # Process block
                            block = await self._process_block(session, block_data)
                            
                            # Process transactions
                            block_transactions = block_data.get('blockTransactions', {}).get('transactions', [])
                            if block_transactions:
                                if self.config['bulk_insert']:
                                    try:
                                        await self._process_transactions_bulk(session, block, block_transactions)
                                    except Exception as tx_error:
                                        if "ForeignKeyViolation" in str(tx_error) or "foreign key constraint" in str(tx_error):
                                            logger.warning(
                                                "Foreign key constraint in bulk process, falling back to individual",
                                                height=block_data.get('height')
                                            )
                                            # Fall back to individual transaction processing
                                            await self._process_transactions(session, block, block_transactions)
                                        else:
                                            raise
                                else:
                                    await self._process_transactions(session, block, block_transactions)
                            else:
                                logger.warning("No transactions in block", height=block_data.get('height'))
                            
                            # Update progress counters without commit
                            self.stats['blocks_processed'] += 1
                            
                        except Exception as e:
                            logger.error(
                                "Error processing block in batch",
                                height=block_data.get('height'),
                                error=str(e),
                                exc_info=True
                            )
                            # If it's a foreign key violation, it usually means we're trying to process blocks too quickly
                            if "ForeignKeyViolation" in str(e) or "foreign key constraint" in str(e):
                                logger.warning(
                                    "Foreign key constraint violation indicates referential integrity issue. Consider processing sequentially.",
                                    height=block_data.get('height')
                                )
                                # Process this specific block individually
                                await self._process_height(block_data.get('height'))
                            else:
                                # Continue with next block instead of failing the entire batch for other errors
                                self.stats['errors'] += 1
                                continue
                            
                    # Commit happens at the end of the context manager
                    
                except Exception as e:
                    logger.error(
                        "Fatal error processing blocks sub-batch",
                        error=str(e),
                        exc_info=True
                    )
                    self.stats['errors'] += 1
                    # Try to process each block in the batch individually as a fallback
                    for block_data in sub_batch:
                        try:
                            height = block_data.get('height')
                            logger.info(f"Falling back to sequential processing for block {height}")
                            await self._process_height(height)
                        except Exception as individual_error:
                            logger.error(
                                "Error in individual block fallback",
                                height=block_data.get('height'),
                                error=str(individual_error)
                            )
        
        logger.info(f"Successfully processed batch of {block_count} blocks")
        return True

    @timed("process_block_with_transactions")
    async def _process_block_with_transactions(self, block_data: Dict[str, Any]):
        """Process a single block and its transactions atomically."""
        block_height = block_data.get('height')
        logger.info("Processing block with transactions", height=block_height)
        
        # Validate block data
        try:
            self._validate_block_data(block_data)
        except ValueError as e:
            logger.error(
                "Block data validation failed",
                height=block_height,
                error=str(e),
                exc_info=True
            )
            raise
            
        async with batch_operation_context() as session:
            try:
                # Process block
                block = await self._process_block(session, block_data)
                
                # Process transactions
                block_transactions = block_data.get('blockTransactions', {}).get('transactions', [])
                if block_transactions:
                    if self.config['bulk_insert']:
                        await self._process_transactions_bulk(session, block, block_transactions)
                    else:
                        await self._process_transactions(session, block, block_transactions)
                else:
                    logger.warning("No transactions in block", height=block_height)
                
                await session.commit()
                logger.info("Successfully processed block with transactions", height=block_height)
                return True
                
            except Exception as e:
                logger.error(
                    "Error processing block with transactions",
                    height=block_height,
                    error=str(e),
                    exc_info=True
                )
                raise

    @timed("process_height")
    async def _process_height(self, height: int):
        """Process a single block height (legacy sequential method)."""
        logger.info("Processing height", height=height)
        
        async with get_session() as session:
            try:
                # Get block data
                logger.debug("Fetching block data from node", height=height)
                block_data = await self.node.get_block_by_height(height)
                logger.debug(
                    "Received block data",
                    height=height,
                    block_id=block_data.get('id'),
                    has_transactions=bool(block_data.get('blockTransactions', {}).get('transactions'))
                )
                
                # Validate block data
                try:
                    self._validate_block_data(block_data)
                except ValueError as e:
                    logger.error(
                        "Block data validation failed",
                        height=height,
                        error=str(e),
                        exc_info=True
                    )
                    raise
                
                # Process block
                block = await self._process_block(session, block_data)
                
                # Process transactions
                block_transactions = block_data.get('blockTransactions', {}).get('transactions', [])
                if block_transactions:
                    if self.config['bulk_insert']:
                        await self._process_transactions_bulk(session, block, block_transactions)
                    else:
                        await self._process_transactions(session, block, block_transactions)
                else:
                    logger.warning("No transactions in block", height=height)
                
                # Update sync status
                status = await self._get_or_create_sync_status(session)
                status.current_height = height
                
                await session.commit()
                self.stats['blocks_processed'] += 1
                logger.info("Successfully processed height", height=height)
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(
                    "Error processing height",
                    height=height,
                    error=str(e),
                    exc_info=True
                )
                raise

    @timed("process_block")
    async def _process_block(self, session: AsyncSession, block_data: Dict[str, Any]) -> Block:
        """Process and store block data."""
        try:
            # Extract header data
            header = block_data['header']
            txs = block_data['blockTransactions']
            
            # Calculate transaction stats
            transactions = txs.get('transactions', [])
            txs_count = len(transactions)
            txs_size = sum(tx.get('size', 0) for tx in transactions)
            
            # Calculate total block coins
            block_coins = sum(
                sum(out.get('value', 0) for out in tx.get('outputs', []))
                for tx in transactions
            )
            
            # Handle genesis block differently
            parent_id = header['parentId']
            if block_data['height'] == 1:
                parent_id = None
            
            # Extract PoW solutions
            pow_solutions = {
                'pk': header.get('powSolutions', {}).get('pk'),
                'w': header.get('powSolutions', {}).get('w'),
                'n': header.get('powSolutions', {}).get('n'),
                'd': header.get('powSolutions', {}).get('d')
            }
            
            # Create block
            block = Block(
                id=block_data['id'],
                header_id=header.get('id', block_data['id']),
                parent_id=parent_id,
                height=block_data['height'],
                timestamp=header['timestamp'],
                difficulty=int(header['difficulty']),
                block_size=txs.get('size', 0),
                block_coins=block_coins,
                block_mining_time=None,  # Will be calculated from parent block
                txs_count=txs_count,
                txs_size=txs_size,
                miner_address=None,  # Will be extracted from coinbase
                miner_name=None,
                main_chain=True,
                version=header['version'],
                transactions_root=header.get('transactionsRoot'),
                state_root=header.get('stateRoot'),
                pow_solutions=pow_solutions
            )
            session.add(block)

            # Process mining reward
            if transactions:
                coinbase_tx = transactions[0]  # First transaction is coinbase
                await self._process_mining_reward(session, block, coinbase_tx)

            performance_tracker.increment_counter("blocks_processed")
            return block
            
        except Exception as e:
            logger.error(
                "Error processing block",
                block_id=block_data.get('id'),
                error=str(e),
                exc_info=True
            )
            raise

    @timed("process_transactions_bulk")
    async def _process_transactions_bulk(self, session: AsyncSession, block: Block, transactions: List[Dict[str, Any]]):
        """Process multiple transactions with bulk operations for better performance."""
        try:
            # Prepare data structures for bulk inserts
            tx_objects = []
            tx_ids = []  # Keep track of transaction IDs for reference
            input_mappings = []
            output_mappings = []
            asset_mappings = []
            address_set = set()  # Unique addresses for address stats
            
            # First transaction is coinbase/mining reward
            is_coinbase = True
            
            # Process each transaction
            for tx_index, tx_data in enumerate(transactions):
                try:
                    # Validate transaction data
                    self._validate_transaction_data(tx_data)
                    
                    # Extract transaction data
                    tx_id = tx_data['id']
                    tx_ids.append(tx_id)
                    
                    # Calculate fee (skip for coinbase)
                    fee = 0
                    if not is_coinbase:
                        inputs_sum = sum(input.get('value', 0) for input in tx_data.get('inputs', []))
                        outputs_sum = sum(output.get('value', 0) for output in tx_data.get('outputs', []))
                        fee = inputs_sum - outputs_sum
                    
                    # Create transaction mapping
                    tx_mapping = {
                        'id': tx_id,
                        'block_id': block.id,
                        'header_id': block.header_id,
                        'inclusion_height': block.height,
                        'timestamp': block.timestamp,
                        'index': tx_index,
                        'main_chain': True,
                        'size': tx_data.get('size', 0),
                        'fee': fee if fee > 0 else 0
                    }
                    tx_objects.append(tx_mapping)
                    
                    # Process inputs (skip for coinbase)
                    if not is_coinbase:
                        for input_idx, input_data in enumerate(tx_data.get('inputs', [])):
                            box_id = input_data.get('boxId')
                            if not box_id:
                                continue
                                
                            input_mapping = {
                                'box_id': box_id,
                                'tx_id': tx_id,
                                'index_in_tx': input_idx,
                                'proof_bytes': input_data.get('spendingProof', {}).get('proofBytes'),
                                'extension': input_data.get('spendingProof', {}).get('extension', {}),
                                'created_at': datetime.utcnow()
                            }
                            input_mappings.append(input_mapping)
                    
                    # Process outputs
                    for output_idx, output_data in enumerate(tx_data.get('outputs', [])):
                        box_id = output_data.get('boxId')
                        if not box_id:
                            continue
                            
                        # Extract address if available
                        address = output_data.get('address')
                        if address:
                            address_set.add(address)
                            
                        # Create output mapping
                        output_mapping = {
                            'box_id': box_id,
                            'tx_id': tx_id,
                            'index_in_tx': output_idx,
                            'value': output_data.get('value', 0),
                            'creation_height': output_data.get('creationHeight', block.height),
                            'address': address,
                            'ergo_tree': output_data.get('ergoTree', ''),
                            'additional_registers': output_data.get('additionalRegisters', {}),
                            'spent_by_tx_id': None,  # Will be updated when spent
                            'created_at': datetime.utcnow()
                        }
                        output_mappings.append(output_mapping)
                        
                        # Process assets in the output
                        assets = output_data.get('assets', [])
                        for asset_idx, asset_data in enumerate(assets):
                            token_id = asset_data.get('tokenId')
                            if not token_id:
                                continue
                                
                            asset_mapping = {
                                'id': f"{box_id}_{asset_idx}",
                                'box_id': box_id,
                                'index_in_outputs': asset_idx,
                                'token_id': token_id,
                                'amount': asset_data.get('amount', 0),
                                'name': None,  # Will be filled later from token info
                                'decimals': None,
                                'created_at': datetime.utcnow()
                            }
                            asset_mappings.append(asset_mapping)
                    
                    # Next transaction is not coinbase
                    is_coinbase = False
                    
                except Exception as e:
                    logger.error(
                        "Error processing transaction in bulk",
                        tx_id=tx_data.get('id'),
                        error=str(e),
                        exc_info=True
                    )
                    raise
            
            # Perform bulk inserts
            if tx_objects:
                await bulk_insert_mappings(session, Transaction, tx_objects)
                self.stats['transactions_processed'] += len(tx_objects)
            
            if input_mappings:
                await bulk_insert_mappings(session, Input, input_mappings)
                self.stats['inputs_processed'] += len(input_mappings)
            
            if output_mappings:
                await bulk_insert_mappings(session, Output, output_mappings)
                self.stats['outputs_processed'] += len(output_mappings)
            
            if asset_mappings:
                await bulk_insert_mappings(session, Asset, asset_mappings)
                self.stats['assets_processed'] += len(asset_mappings)
            
            # Process address stats
            if address_set:
                await self._process_address_stats_bulk(session, address_set, block.timestamp)
            
            logger.info(
                "Bulk processed transactions",
                block_height=block.height,
                tx_count=len(tx_objects),
                inputs=len(input_mappings),
                outputs=len(output_mappings),
                assets=len(asset_mappings),
                addresses=len(address_set)
            )
            
        except Exception as e:
            logger.error(
                "Error in bulk transaction processing",
                block_id=block.id,
                height=block.height,
                error=str(e),
                exc_info=True
            )
            raise

    @timed("process_address_stats_bulk")
    async def _process_address_stats_bulk(self, session: AsyncSession, addresses: Set[str], timestamp: int):
        """Process address statistics in bulk."""
        address_mappings = []
        
        for address in addresses:
            # Check if address stats already exist
            result = await session.execute(
                select(AddressStats).where(AddressStats.address == address)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update last active time if newer
                if existing.last_active_time is None or timestamp > existing.last_active_time:
                    existing.last_active_time = timestamp
            else:
                # Create new address stats
                address_type = self._determine_address_type(address)
                script_complexity = 0
                
                address_stats = {
                    'address': address,
                    'first_active_time': timestamp,
                    'last_active_time': timestamp,
                    'address_type': address_type,
                    'script_complexity': script_complexity,
                    'created_at': datetime.utcnow()
                }
                address_mappings.append(address_stats)
        
        # Bulk insert new address stats
        if address_mappings:
            await bulk_insert_mappings(session, AddressStats, address_mappings)
            logger.debug(f"Inserted {len(address_mappings)} new address stats")

    # Keep the existing methods below with their current implementation
    async def _process_mining_reward(self, session: AsyncSession, block: Block, coinbase_tx: Dict[str, Any]):
        # ... existing implementation ...
        pass

    async def _process_transactions(self, session: AsyncSession, block: Block, transactions: List[Dict[str, Any]]):
        # ... existing implementation ...
        pass

    async def _update_spent_outputs(self, session: AsyncSession, tx_id: str, inputs: List[Dict[str, Any]]):
        # ... existing implementation ...
        pass

    def _determine_address_type(self, address: str) -> str:
        # ... existing implementation ...
        pass

    def _calculate_script_complexity(self, ergo_tree: str) -> int:
        # ... existing implementation ...
        pass

    async def _process_block_with_semaphore(self, semaphore: asyncio.Semaphore, height: int):
        """Process a block with semaphore to limit concurrency."""
        async with semaphore:
            try:
                # Get block data
                block_data = await self.node.get_block_by_height(height)
                
                # Process the block
                result = await self._process_block_with_transactions(block_data)
                return result
            except Exception as e:
                logger.error("Error in processing block with semaphore", 
                            height=height, error=str(e))
                raise 