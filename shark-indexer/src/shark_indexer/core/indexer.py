import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import registry

from ..db.models import Block, Transaction, Input, Output, Asset, SyncStatus, MiningReward, AddressStats, mapper_registry
from ..db.database import get_session
from .node import NodeClient

logger = structlog.get_logger()

class IndexerService:
    def __init__(self, node_client: NodeClient):
        self.node = node_client
        self.is_running = False
        self.current_height = 0
        self.target_height = 0

    async def start(self):
        """Start the indexer service."""
        if self.is_running:
            return

        self.is_running = True
        try:
            await self._run_indexer()
        finally:
            self.is_running = False

    async def stop(self):
        """Stop the indexer service."""
        self.is_running = False

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

                # Process next block
                await self._process_height(self.current_height + 1)
                self.current_height += 1

            except Exception as e:
                logger.error("Error in indexer loop", error=str(e), exc_info=True)
                await asyncio.sleep(5)

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

    async def _process_height(self, height: int):
        """Process a single block height."""
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
                    parent_id=block_data.get('parentId'),
                    timestamp=block_data.get('timestamp'),
                    difficulty=block_data.get('difficulty'),
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
                        block_data=block_data,
                        exc_info=True
                    )
                    raise
                
                # Process block
                block = await self._process_block(session, block_data)
                
                # Process transactions
                block_transactions = block_data.get('blockTransactions', {}).get('transactions', [])
                if block_transactions:
                    await self._process_transactions(session, block, block_transactions)
                else:
                    logger.warning("No transactions in block", height=height)
                
                # Update sync status
                status = await self._get_or_create_sync_status(session)
                status.current_height = height
                
                await session.commit()
                logger.info("Successfully processed height", height=height)
                
            except Exception as e:
                logger.error(
                    "Error processing height",
                    height=height,
                    error=str(e),
                    exc_info=True
                )
                raise

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

            return block
            
        except Exception as e:
            logger.error(
                "Error processing block",
                block_id=block_data.get('id'),
                error=str(e),
                exc_info=True
            )
            raise

    async def _process_mining_reward(
        self,
        session: AsyncSession,
        block: Block,
        coinbase_tx: Dict[str, Any]
    ):
        """Process mining reward from coinbase transaction."""
        try:
            # Extract miner's address from first output
            if coinbase_tx.get('outputs'):
                miner_output = coinbase_tx['outputs'][0]
                miner_address = miner_output.get('address')
                reward_amount = miner_output.get('value', 0)

                # Calculate total fees (sum of all inputs minus outputs)
                total_fees = sum(
                    sum(out.get('value', 0) for out in tx.get('outputs', []))
                    for tx in block.transactions
                ) - reward_amount

                # Create mining reward record
                mining_reward = MiningReward(
                    block_id=block.id,
                    reward_amount=reward_amount,
                    fees_amount=total_fees,
                    miner_address=miner_address
                )
                session.add(mining_reward)

                # Update block with miner info
                block.miner_address = miner_address

        except Exception as e:
            logger.error(
                "Error processing mining reward",
                block_id=block.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def _process_transactions(
        self,
        session: AsyncSession,
        block: Block,
        transactions: List[Dict[str, Any]]
    ):
        """Process block transactions."""
        for index, tx_data in enumerate(transactions):
            try:
                # Validate transaction data
                self._validate_transaction_data(tx_data)
                
                # Calculate transaction fee - Fix for async generator issue
                # Replace the sum() with explicit awaits
                inputs_sum = 0
                for input_box in tx_data.get('inputs', []):
                    box_value = await self._get_output_value(session, input_box['boxId'])
                    inputs_sum += box_value
                
                outputs_sum = sum(
                    output.get('value', 0)
                    for output in tx_data.get('outputs', [])
                )
                fee = inputs_sum - outputs_sum if inputs_sum > outputs_sum else 0
                
                # Create transaction
                tx = Transaction(
                    id=tx_data['id'],
                    block_id=block.id,
                    header_id=block.header_id,
                    inclusion_height=block.height,
                    timestamp=block.timestamp,
                    index=index,
                    main_chain=block.main_chain,
                    size=tx_data.get('size', 0),
                    fee=fee
                )
                session.add(tx)
                
                # Process inputs
                for input_index, input_data in enumerate(tx_data.get('inputs', [])):
                    input_box = Input(
                        box_id=input_data['boxId'],
                        tx_id=tx.id,
                        index_in_tx=input_index,
                        proof_bytes=input_data.get('proofBytes'),
                        extension=input_data.get('extension')
                    )
                    session.add(input_box)
                
                # Process outputs
                for output_index, output_data in enumerate(tx_data.get('outputs', [])):
                    output = Output(
                        box_id=output_data['boxId'],
                        tx_id=tx.id,
                        index_in_tx=output_index,
                        value=output_data['value'],
                        creation_height=output_data['creationHeight'],
                        address=output_data.get('address'),
                        ergo_tree=output_data['ergoTree'],
                        additional_registers=output_data.get('additionalRegisters', {})
                    )
                    session.add(output)
                    
                    # Update address stats
                    if output.address:
                        await self._update_address_stats(
                            session,
                            output.address,
                            block.timestamp,
                            output.ergo_tree
                        )
                    
                    # Process assets
                    for asset_index, asset_data in enumerate(output_data.get('assets', [])):
                        asset = Asset(
                            id=f"{output.box_id}_{asset_index}",
                            box_id=output.box_id,
                            index_in_outputs=asset_index,
                            token_id=asset_data['tokenId'],
                            amount=asset_data['amount'],
                            name=None,  # Will be updated from token_info
                            decimals=None  # Will be updated from token_info
                        )
                        session.add(asset)
                
                await session.flush()
                
            except Exception as e:
                logger.error(
                    "Error processing transaction",
                    tx_id=tx_data.get('id'),
                    error=str(e),
                    exc_info=True
                )
                raise

    async def _get_output_value(self, session: AsyncSession, box_id: str) -> int:
        """Get the value of an output box."""
        result = await session.execute(
            select(Output.value).where(Output.box_id == box_id)
        )
        value = result.scalar_one_or_none()
        return value or 0

    async def reorg_from_height(self, height: int):
        """Handle chain reorganization from specified height."""
        logger.warning("Handling chain reorganization", height=height)
        
        async with get_session() as session:
            # Delete blocks from height onwards
            await session.execute(
                select(Block).where(Block.height >= height)
            )
            
            # Update sync status
            status = await self._get_or_create_sync_status(session)
            status.current_height = height - 1
            
            await session.commit()
            
        # Reset current height
        self.current_height = height - 1 

    async def _update_address_stats(
        self,
        session: AsyncSession,
        address: str,
        timestamp: int,
        ergo_tree: str
    ):
        """Update address statistics."""
        try:
            # Get or create address stats
            stats = await session.get(AddressStats, address)
            if not stats:
                stats = AddressStats(
                    address=address,
                    first_active_time=timestamp,
                    last_active_time=timestamp,
                    address_type=self._determine_address_type(ergo_tree),
                    script_complexity=self._calculate_script_complexity(ergo_tree)
                )
                session.add(stats)
            else:
                stats.last_active_time = max(stats.last_active_time, timestamp)
                stats.first_active_time = min(stats.first_active_time, timestamp)

        except Exception as e:
            logger.error(
                "Error updating address stats",
                address=address,
                error=str(e),
                exc_info=True
            )
            raise

    def _determine_address_type(self, ergo_tree: str) -> str:
        """Determine address type from ErgoTree."""
        # Simple heuristic based on script length
        if len(ergo_tree) < 1000:
            return 'p2pk'  # Pay to public key
        elif 'TOKEN' in ergo_tree:
            return 'token_contract'
        else:
            return 'smart_contract'

    def _calculate_script_complexity(self, ergo_tree: str) -> int:
        """Calculate script complexity score."""
        # Simple heuristic based on script length and operations
        base_score = len(ergo_tree) // 100
        op_count = ergo_tree.count('CONST') + ergo_tree.count('IF')
        return base_score + op_count 