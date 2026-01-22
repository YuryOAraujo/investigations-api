from fastapi import Query
from typing import Optional

class PaginationParams:
  def __init__(
    self,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query('created_at', pattern='^(id|title|status|created_at)$'),
    sort_order: str = Query('desc', pattern='^(asc|desc)$')
  ):
    self.skip = skip
    self.limit = limit
    self.sort_by = sort_by
    self.sort_order = sort_order
    
class FilterParams:
  def __init__(
    self,
    status: Optional[str] = Query(None, pattern='^(open|closed|pending)$'),
    title: Optional[str] = Query(None, min_length=1)
  ):
    self.status = status
    self.title = title