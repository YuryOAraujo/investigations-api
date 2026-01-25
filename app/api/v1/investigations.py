from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO
from ...services.minio_service import minio_service
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from ...db import SessionLocal
from ...models import Investigation
from ...schemas import InvestigationCreate, InvestigationUpdate, InvestigationResponse
from ...auth import require_role
from ...dependencies import PaginationParams, FilterParams
from ...services.kafka_service import kafka_service

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

@router.post('', response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation(
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

  await kafka_service.publish_event(
    event_type='created',
    investigation_id=investigation.id,
    data={
      'title': investigation.title,
      'status': investigation.status
    },
    user={'username': user.get('preferred_username')}
  )
  
  return investigation

@router.put('/{investigation_id}', response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
async def update_investigation(
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
  
  old_data = {
    'title': investigation.title,
    'status': investigation.status
  }
  
  investigation.title = data.title
  investigation.status = data.status
  db.commit()
  db.refresh(investigation)

  await kafka_service.publish_event(
    event_type='updated',
    investigation_id=investigation.id,
    data={
      'old': old_data,
      'new': {
        'title': investigation.id,
        'status': investigation.status
      }
    },
    user={'username': user.get('preferred_username')}
  )
  
  return investigation

@router.patch('/{investigation_id}', response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
async def partial_update_investigation(
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
  
  changes = {}
  update_data = data.model_dump(exclude_unset=True)

  for field, value in update_data.items():
    changes[field] = {
      'old': getattr(investigation, field),
      'new': value
    }
    setattr(investigation, field, value)
  
  db.commit()
  db.refresh(investigation)

  await kafka_service.publish_event(
    event_type='updated',
    investigation_id=investigation.id,
    data={'changes': changes},
    user={'username': user.get('preferred_username')}
  )
  
  return investigation

@router.delete('/{investigation_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_investigation(
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
  
  investigation_data = {
    'title': investigation.title,
    'status': investigation.status
  }
  
  if investigation.pdf_file_path:
    try:
      minio_service.delete_pdf(investigation.pdf_file_path)
    except Exception:
      pass

  db.delete(investigation)
  db.commit()

  await kafka_service.publish_event(
    event_type='deleted',
    investigation_id=investigation_id,
    data=investigation_data,
    user={'username': user.get('preferred_username')}
  )

@router.post('/{investigation_id}/upload-pdf', status_code=status.HTTP_200_OK)
async def upload_investigation_pdf(
    investigation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(require_role('admin'))
):
  '''Upload a PDF file for an investigation.'''
  
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
  if not investigation:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f'Investigation {investigation_id} not found'
    )
  
  if not file.filename.endswith('.pdf'):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail='Only PDF files are allowed'
    )
  
  contents = await file.read()
  if len(contents) > 10 * 1024 * 1024:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail='File size exceeds 10MB limit'
    )
  
  if investigation.pdf_file_path:
    try:
      minio_service.delete_pdf(investigation.pdf_file_path)
    except Exception:
      pass
  
  try:
    object_path = minio_service.upload_pdf(contents, investigation_id, file.filename)
    investigation.pdf_file_path = object_path
    db.commit()

    await kafka_service.publish_event(
      event_type='pdf_uploaded',
      investigation_id=investigation_id,
      data={
          'filename': file.filename,
          'file_path': object_path,
          'file_size': len(contents)
      },
      user={'username': user.get('preferred_username')}
    )
    
    return {
      'message': 'PDF uploaded successfully',
      'file_path': object_path
    }
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f'Error uploading file: {str(e)}'
    )

@router.get('/{investigation_id}/pdf', status_code=status.HTTP_200_OK)
def download_investigation_pdf(
    investigation_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role('investigator'))
):
  '''Download the PDF file for an investigation.'''
  
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
  if not investigation:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f'Investigation {investigation_id} not found'
    )
  
  if not investigation.pdf_file_path:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='No PDF file attached to this investigation'
    )
  
  try:
    pdf_data = minio_service.download_pdf(investigation.pdf_file_path)
    
    return StreamingResponse(
      BytesIO(pdf_data),
      media_type='application/pdf',
      headers={
       'Content-Disposition': f'attachment; filename="investigation_{investigation_id}.pdf"'
      }
    )
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f'Error downloading file: {str(e)}'
    )
  
@router.delete('/{investigation_id}/pdf', status_code=status.HTTP_204_NO_CONTENT)
def delete_investigation_pdf(
    investigation_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role('admin'))
):
  '''Delete the PDF file for an investigation.'''
  
  investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
  if not investigation:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f'Investigation {investigation_id} not found'
    )
  
  if not investigation.pdf_file_path:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='No PDF file attached to this investigation'
    )
  
  try:
    minio_service.delete_pdf(investigation.pdf_file_path)
    investigation.pdf_file_path = None
    db.commit()
  except Exception as e:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f'Error deleting file: {str(e)}'
    )
  
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