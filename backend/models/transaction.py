from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import Optional

from .user import PyObjectId

class Transaction(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    user_id: PyObjectId
    type: str
    amount_cr: int = 0
    amount_pay: float = 0.0
    related_ticket: Optional[PyObjectId]
    approved_by: Optional[PyObjectId]
    ts: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
