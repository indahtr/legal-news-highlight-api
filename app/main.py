from fastapi import FastAPI
from app.routers import highlight_router

app = FastAPI(
    title="Law News Highlight API",
    description="API untuk menghasilkan highlight berita hukum online.",
    version="0.3.0"
)

app.include_router(highlight_router)
