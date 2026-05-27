import os
import threading
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database.session import get_db
from models.user import User
from api.deps import get_verified_user

router = APIRouter(prefix="/admin", tags=["admin"])

ingest_status = {"running": False, "result": None}


def _run_ingest():
    """Run card ingest in background thread."""
    try:
        ingest_status["running"] = True
        ingest_status["result"] = "running..."

        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scripts.ingest_cards import download_cards, generate_ai_tags, build_embedding_text, generate_embeddings, store_cards

        # Step 1: Download
        cards = download_cards()
        ingest_status["result"] = f"Downloaded {len(cards)} cards"

        # Step 2: Load seed tags (skip AI tagging)
        import json
        from pathlib import Path
        seed_path = Path(os.path.dirname(os.path.abspath(__file__))).parent / "scripts" / "seed_tags.json"
        tags = []
        if seed_path.exists():
            with open(seed_path) as f:
                tags = json.load(f)
            ingest_status["result"] = f"Loaded {len(tags)} seed tags"
        else:
            ingest_status["result"] = "No seed tags found!"
            ingest_status["running"] = False
            return

        # Step 3: Embeddings
        tag_lookup = {t["name"].lower(): t for t in tags}
        texts = [
            build_embedding_text(card, tag_lookup.get(card["name"].lower()))
            for card in cards
        ]
        embeddings = generate_embeddings(texts)
        ingest_status["result"] = f"Generated {len(embeddings)} embeddings"

        # Step 4: Store
        store_cards(cards, tags, embeddings)
        ingest_status["result"] = f"Complete: {len(cards)} cards stored"

    except Exception as e:
        ingest_status["result"] = f"Error: {str(e)}"
    finally:
        ingest_status["running"] = False


@router.post("/ingest-cards")
async def trigger_ingest(
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """Trigger card database ingest. Admin only."""
    # Simple admin check — only your email
    if user.email != os.getenv("ADMIN_EMAIL", "jellisedens@gmail.com"):
        raise HTTPException(status_code=403, detail="Admin only")

    if ingest_status["running"]:
        return {"status": "already_running", "progress": ingest_status["result"]}

    # Run in background thread
    thread = threading.Thread(target=_run_ingest, daemon=True)
    thread.start()

    return {"status": "started", "message": "Ingest running in background. Check /admin/ingest-status"}


@router.get("/ingest-status")
async def get_ingest_status(
    user: User = Depends(get_verified_user),
):
    """Check ingest progress."""
    return {
        "running": ingest_status["running"],
        "result": ingest_status["result"],
    }