from fastapi import APIRouter

from app.schemas import HighlightRequest, HighlightResponse
from app.services.summarizer_service import generate_highlight_from_text

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "API is running"}

@router.post("/highlight", response_model=HighlightResponse)
async def highlight_endpoint(request: HighlightRequest):
        
    highlight = generate_highlight_from_text(
        content=request.content,
        max_length=request.max_length,
        min_length=request.min_length,
        no_repeat_ngram_size=request.no_repeat_ngram_size
    )

    return HighlightResponse(highlight=highlight)