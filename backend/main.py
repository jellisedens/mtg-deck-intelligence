from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.health import router as health_router

app = FastAPI(
    title="MTG Deck Intelligence",
    description="AI-powered Magic: The Gathering deck building and analytics",
    version="0.1.0",
)

# CORS — allow frontend dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)


@app.get("/")
def root():
    return {"message": "MTG Deck Intelligence API", "docs": "/docs"}