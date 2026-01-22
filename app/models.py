from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Investigation(Base):
  __tablename__ = "investigations"

  id: Mapped[int] = mapped_column(primary_key=True)
  title: Mapped[str] = mapped_column(String(255), nullable=False)
  status: Mapped[str] = mapped_column(String(50), default="open")
  created_at: Mapped[str] = mapped_column(
      DateTime(timezone=True),
      server_default=func.now()
  )
