from fastapi import APIRouter
from . import investigations

v1_router = APIRouter(prefix='/v1')
v1_router.include_router(investigations.router)