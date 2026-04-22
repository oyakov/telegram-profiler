from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
