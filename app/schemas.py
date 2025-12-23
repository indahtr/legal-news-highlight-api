
from pydantic import BaseModel

class HighlightRequest(BaseModel):
    content: str
    max_length: int = 75
    min_length: int = 30
    no_repeat_ngram_size: int = 2


class HighlightResponse(BaseModel):
    highlight: str
