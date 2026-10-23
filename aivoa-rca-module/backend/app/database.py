import os, json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rca_demo.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
class InvestigationRecord(Base):
    __tablename__ = "investigations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(240), default="Untitled investigation")
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    batch_number: Mapped[str] = mapped_column(String(120), default="")
    product_name: Mapped[str] = mapped_column(String(240), default="")
    data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

def init_db(): Base.metadata.create_all(bind=engine)
def serialize_record(record):
    data=json.loads(record.data_json)
    data.update({"id":record.id,"title":record.title,"status":record.status,"batch_number":record.batch_number,"product_name":record.product_name,"created_at":record.created_at.isoformat() if record.created_at else None,"updated_at":record.updated_at.isoformat() if record.updated_at else None})
    return data
