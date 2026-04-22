from typing import Optional
from pydantic import BaseModel

class SettingUpdate(BaseModel):
    value: str
    value_type: str = "string"
    description: Optional[str] = None
    category: str = "general"
