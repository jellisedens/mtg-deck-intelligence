from database.session import SessionLocal
from models.deck import Deck
from models.user import User
import json

db = SessionLocal()
user = db.query(User).filter(User.email == "test@mtg.com").first()
deck = db.query(Deck).filter(Deck.user_id == user.id).first()
tags = deck.strategy_profile.get("sim_tags", {})

check_cards = [
    "cultivate",
    "stomping ground",
    "terror of the peaks",
    "the ur-dragon",
    "nature's lore",
    "lathliss, dragon queen",
    "sol ring",
    "command tower",
    "dragon tempest",
    "farseek",
]

for name in check_cards:
    t = tags.get(name, {})
    print(f"=== {name.upper()} ===")
    print(json.dumps(t, indent=2))
    print()

db.close()