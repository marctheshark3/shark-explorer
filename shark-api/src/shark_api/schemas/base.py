"""Base schemas for API responses."""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    code: str
    details: Optional[dict] = None

class PaginatedResponse(GenericModel, Generic[T]):
    """Paginated response schema."""
    items: List[T]
    total: int
    page: int
    page_size: int
    
class TimestampMixin(BaseModel):
    """Timestamp mixin for responses."""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None 