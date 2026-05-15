from typing import Any, Optional
from pydantic import BaseModel


class SuccessResponse(BaseModel):
	success: bool = True
	message: str
	data: Optional[Any] = None


class ErrorResponse(BaseModel):
	success: bool = False
	message: str
	error: Optional[Any] = None


