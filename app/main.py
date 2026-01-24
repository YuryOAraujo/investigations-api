from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .services.kafka_service import kafka_service
from .db import engine
from .models import Base
from .api.v1.router import v1_router

@asynccontextmanager
async def lifespan(app: FastAPI):
  await kafka_service.start_producer()
  yield
  await kafka_service.stop_producer()

app = FastAPI(
  title='Investigation API',
  version='1.0.0',
  description='API for managing investigations',
  lifespan=lifespan
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

# Allow alembic to manage table migrations, instead of relying on app to do so
# @app.on_event('startup')
# def startup():
#   Base.metadata.create_all(bind=engine)

app.include_router(v1_router, prefix='/api')

@app.get('/health', tags=['health'])
def health():
  return {'status': 'ok', 'version': '1.0.0'}