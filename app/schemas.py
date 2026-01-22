from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class InvestigationBase(BaseModel):
  title: str = Field(..., min_length=1, max_length=255)
  status: str = Field(default='open', pattern='^(open|closed|pending)$')

class InvestigationCreate(InvestigationBase):
  pass

class InvestigationUpdate(BaseModel):
  title: Optional[str] = Field(None, min_length=1, max_length=255)
  status: Optional[str] = Field(None, pattern='^(open|closed|pending)$')

class InvestigationResponse(InvestigationBase):
  id: int
  created_at: datetime

  model_config = ConfigDict(from_attributes=True)

class PaginationParams(BaseModel):
  skip: int = Field(0, ge=0)
  limit: int = Field(10, get=1, le=100)
  sort_by: str = Field('created_at')
  sort_order: str = Field('desc', pattern='^(asc|desc)$')