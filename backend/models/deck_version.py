import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.session import Base


class DeckVersion(Base):
    __tablename__ = "deck_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    card_snapshot = Column(JSON, nullable=False)
    analytics_snapshot = Column(JSON, nullable=True)
    strategy_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    deck = relationship("Deck", back_populates="versions")

    def __repr__(self):
        return f"<DeckVersion {self.version_number} for deck {self.deck_id}>"