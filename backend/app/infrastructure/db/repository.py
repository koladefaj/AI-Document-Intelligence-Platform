from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.models import Document, ChatMessage

class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, doc_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_by_owner(self, owner_id: UUID) -> list[Document]:
        result = await self.session.execute(
            select(Document).where(Document.owner_id == owner_id)
        )
        return result.scalars().all()

    async def delete(self, doc: Document) -> None:
        await self.session.delete(doc)
        await self.session.commit()

    # --- CHAT PERSISTENCE ---
    async def get_chat_history(self, doc_id: UUID, user_id: UUID) -> list[ChatMessage]:
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.document_id == doc_id, ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return result.scalars().all()

    async def add_chat_message(self, doc_id: UUID, user_id: UUID, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(document_id=doc_id, user_id=user_id, role=role, content=content)
        self.session.add(msg)
        await self.session.commit()
        return msg
