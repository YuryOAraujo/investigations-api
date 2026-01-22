from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine
from .models import Base
from .api.v1.router import v1_router

app = FastAPI(
  title='Investigation API',
  version='1.0.0',
  description='API for managing investigations'
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

@app.on_event('startup')
def startup():
  Base.metadata.create_all(bind=engine)

app.include_router(v1_router, prefix='/api')

@app.get('/health', tags=['health'])
def health():
  return {'status': 'ok', 'version': '1.0.0'}