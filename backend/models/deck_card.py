import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.session import Base


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False)
    scryfall_id = Column(String, nullable=False)
    card_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    board = Column(String, nullable=False, default="main")

    # Relationships
    deck = relationship("Deck", back_populates="cards")

    def __repr__(self):
        return f"<DeckCard {self.card_name} x{self.quantity} ({self.board})>"