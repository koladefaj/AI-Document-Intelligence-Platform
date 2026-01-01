import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """
    Base class for all models. 
    Using SQLAlchemy 2.0's DeclarativeBase for full type-hinting support.
    """
    pass

class User(Base):
    __tablename__ = "users"

    # Dev Note: Using native UUID type for better performance in Postgres
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="user"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    # Relationship to documents for easy querying (e.g., user.documents)
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    content: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Dev Note: 'url' typically stores the MinIO link, 'local_path' for processing cache
    url: Mapped[str] = mapped_column(String(500), nullable=True)
    local_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Tracking state: PENDING, PROCESSING, COMPLETED, FAILED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)

    # --- CONTENT & AI ANALYSIS ---
    # raw_text can be massive, so we use Text (CLOB)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    
    # Optimized: Storing analysis as JSON allows for structured queries in Postgres
    analysis: Mapped[dict] = mapped_column(JSON, nullable=True, default={})

    # --- METADATA ---
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    
    # Bidirectional relationship
    owner: Mapped["User"] = relationship("User", back_populates="documents")