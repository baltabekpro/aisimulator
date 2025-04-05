from pydantic import BaseModel
from typing import Optional, Any, List, Dict


class SuccessResponse(BaseModel):
    """Schema for standard success response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorDetail(BaseModel):
    """Schema for error details."""
    loc: Optional[List[str]] = None
    msg: str
    type: str


class ErrorResponse(BaseModel):
    """Schema for standard error response."""
    success: bool = False
    message: str
    detail: Optional[List[ErrorDetail]] = None
    error_code: Optional[str] = None
