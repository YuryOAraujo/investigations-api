from fastapi import FastAPI
from .db import engine
from .models import Base
from sqlalchemy.orm import Session
from fastapi import Depends
from .db import SessionLocal
from .models import Investigation

def get_db():
    db = SessionLocal()
    try: 
      yield db
    finally:
      db.close()

app = FastAPI(title='Investigation API')

@app.post('/investigations')
def create_investigation(title: str, db: Session = Depends(get_db)):
   inv = Investigation(title=title)
   db.add(inv)
   db.commit()
   db.refresh(inv)
   return inv

@app.get('investigations')
def list_investigations(db: Session = Depends(get_db)):
   return db.query(Investigation).all()

@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)

@app.get('/health')
def health():
    return {'status': 'ok'}