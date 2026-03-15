from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env from project root
load_dotenv("../.env")

from app.routers import auth, campaigns, character, game, shop, npc

app = FastAPI(title="Realms of Fate", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(character.router)
app.include_router(game.router)
app.include_router(shop.router)
app.include_router(npc.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
