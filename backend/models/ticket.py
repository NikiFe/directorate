from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import Optional, List, Dict

from .user import PyObjectId

class Ticket(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    body_md: str
    category: str
    sub_category: str
    status: str = "open"
    visibility: str = "hierarchical"
    author_id: PyObjectId
    assignee_id: PyObjectId
    target_rank: str
    watchers: List[PyObjectId] = []
    comments: List[Dict] = []
    reward_credits: int = 0
    reward_pay: float = 0.0
    approval_log: List[Dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
