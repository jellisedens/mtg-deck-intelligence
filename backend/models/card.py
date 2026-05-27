import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from database.session import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scryfall_id = Column(String, unique=True, nullable=False, index=True)
    oracle_id = Column(String, index=True)
    name = Column(String, nullable=False, index=True)
    type_line = Column(String)
    oracle_text = Column(Text)
    mana_cost = Column(String)
    cmc = Column(Float)
    colors = Column(JSON)
    color_identity = Column(JSON)
    legalities = Column(JSON)
    prices = Column(JSON)
    image_uris = Column(JSON)
    power = Column(String)
    toughness = Column(String)
    rarity = Column(String)
    set_code = Column(String)
    keywords = Column(JSON)

    # AI-generated strategic tags
    roles = Column(JSON)
    archetypes = Column(JSON)
    search_terms = Column(JSON)
    synergies = Column(JSON)
    power_level = Column(String)
    strategic_summary = Column(Text)

    edhrec_rank = Column(Integer, nullable=True)
    # Vector embedding
    embedding = Column(Vector(1536))

    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Card {self.name}>"