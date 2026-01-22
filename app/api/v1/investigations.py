from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from ...db import SessionLocal
from ...models import Investigation
from ...schemas import InvestigationCreate, InvestigationUpdate, InvestigationResponse
from ...auth import require_role
from ...dependencies import PaginationParams, FilterParams

router = APIRouter(prefix='/investigations', tags=['investigations'])

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

@router.get('', response_model=dict, status_code=status.HTTP_200_OK)
def list_investigations(
  db: Session = Depends(get_db),
  pagination: PaginationParams = Depends(),
  filters: FilterParams = Depends(),
  user = Depends(require_role('investigator'))
):
  '''
  Get all investigations with pagination, filtering, and sorting.
  
  - **skip**: Number of records to skip (default 0)
  - **limit**: Max records to return (default 10, max 100)
  - **sort_by**: Field to sort by (default created_at)
  - **sort_order**: asc or desc (default desc)
  - **status**: Filter by status (open, closed, pending)
  - **title**: Filter by title (substring match)
  '''  

  query = db.query(Investigation)

  if filters.status:
    query = query.filter(Investigation.status == filters.status)
  if filters.title:
    query = query.filter(Investigation.title.ilike(f'%{filters.title}%'))

  total = query.count()

  sort_column = getattr(Investigation, pagination.sort_by)

  if pagination.sort_order == 'asc':
    query = query.order_by(asc(sort_column))
  else:
    query = query.order_by(desc(sort_column))

  investigations = query.offset(pagination.skip).limit(pagination.limit).all()

  data = [InvestigationResponse.model_validate(inv) for inv in investigations]

  return {
    'data': data,
    'pagination': {
      'skip': pagination.skip,
      'limit': pagination.limit,
      'total': total,
      'returned': len(investigations)
    }
  }

@router.get('/{investigation_id}', response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
def get_investigation(
  investigation_id: int,
  db: Session = Depends(get_db),
  user = Depends(require_role('investigator'))
):
  '''Get a specific investigation by ID.'''
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
  
  if not investigation:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f'Investigation {investigation_id} not found'
    )
  
  return investigation

@router.post('', response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(
  data: InvestigationCreate,
  db: Session = Depends(get_db),
  user = Depends(require_role('admin'))
):
  '''Create a new investigation.'''
  investigation = Investigation(
    title=data.title,
    status=data.status
  )
  db.add(investigation)
  db.commit()
  db.refresh(investigation)
  
  return investigation

@router.put('/{investigation_id}', response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
def update_investigation(
  investigation_id: int,
  data: InvestigationCreate,
  db: Session = Depends(get_db),
  user = Depends(require_role('admin'))
):
  '''
  Fully update an investigation (idempotent).
  PUT is idempotent - calling it multiple times has the same effect as calling once.
  '''
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
  
  if not investigation:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f'Investigation {investigation_id} not found'
    )
  
  investigation.title = data.title
  investigation.status = data.status
  db.commit()
  db.refresh(investigation)
  
  return investigation

@router.patch('/{investigation_id}', response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
def partial_update_investigation(
  investigation_id: int,
  data: InvestigationUpdate,
  db: Session = Depends(get_db),
  user = Depends(require_role('admin'))
):
  '''Partially update an investigation (only provided fields).'''
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
  
  if not investigation:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f'Investigation {investigation_id} not found'
    )
  
  update_data = data.model_dump(exclude_unset=True)
  for field, value in update_data.items():
    setattr(investigation, field, value)
  
  db.commit()
  db.refresh(investigation)
  
  return investigation

@router.delete('/{investigation_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_investigation(
  investigation_id: int,
  db: Session = Depends(get_db),
  user = Depends(require_role('admin'))
):
  '''Delete an investigation.'''
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()

  if not investigation:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f'Investigation {investigation_id} not found'
    )

  db.delete(investigation)
  db.commit()