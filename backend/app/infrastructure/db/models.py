import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, Text, DateTime, JSON, Index, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import VECTOR

class Base(DeclarativeBase):
    """
    Base class for all models.
    """
    pass

class User(Base):
    __tablename__ = "users"

    # Using native UUID type for better performance in Postgres
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

    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
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

    # Cost Tracking: total tokens consumed by this user across all documents
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0)

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
    
    url: Mapped[str] = mapped_column(String(500), nullable=True)
    local_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Content Hash for de-duplication (SHA-256)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    # Tracking state: PENDING, PROCESSING, COMPLETED, FAILED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- CONTENT & AI ANALYSIS ---
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    
    # Storing analysis as JSON allows for structured queries in Postgres
    analysis: Mapped[dict] = mapped_column(JSON, nullable=True, default={})

    # --- METADATA ---
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    
    # Bidirectional relationship
    owner: Mapped["User"] = relationship("User", back_populates="documents")
    embeddings: Mapped[list["DocumentEmbedding"]] = relationship(
        "DocumentEmbedding", 
        back_populates="document",
        cascade="all, delete-orphan"
    )
    chats: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="document",
        cascade="all, delete-orphan"
    )

class ChatMessage(Base):
    """
    Persistent storage for document-specific conversations.
    """
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    role: Mapped[str] = mapped_column(String(20)) # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chats")


class DocumentEmbedding(Base):
    """
    ORM Model for storing document chunks and their vector embeddings.
    Used for semantic search and RAG queries.
    """
    __tablename__ = "data_document_embeddings" # Keep the same name llama-index used for compatibility or migrate

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Vector column (768 for nomic-embed-text)
    embedding: Mapped[list] = mapped_column(VECTOR(768), nullable=False)

    meta: Mapped[dict] = mapped_column(JSON, nullable=True, default={})

    # Relationship back to document
    document: Mapped["Document"] = relationship("Document", back_populates="embeddings")

    # --- Indexing for Performance ---
    __table_args__ = (
        Index(
            'idx_document_embeddings_hnsw', 
            'embedding', 
            postgresql_using='hnsw', 
            postgresql_with={'m': 16, 'ef_construction': 64}, 
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
        {"info": {"vector_index": True}},
    )
