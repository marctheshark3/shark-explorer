"""Base repository class."""
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """Base class for all repositories."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize repository."""
        self.model = model
        self.session = session

    async def get(self, id: Any) -> Optional[ModelType]:
        """Get single record by id."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple records."""
        query = select(self.model)
        
        if filters:
            for field, value in filters.items():
                query = query.where(getattr(self.model, field) == value)
                
        if order_by is not None:
            query = query.order_by(order_by)
            
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records."""
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for field, value in filters.items():
                query = query.where(getattr(self.model, field) == value)
                
        result = await self.session.execute(query)
        return result.scalar_one()

    def filter_query(self, query: Select, filters: Dict[str, Any]) -> Select:
        """Apply filters to query."""
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        return query 