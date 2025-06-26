from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import Optional

from .user import PyObjectId

class Notification(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    user_id: PyObjectId
    message: str
    ticket_id: Optional[PyObjectId]
    read: bool = False
    ts: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
