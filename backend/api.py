from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
from typing import List

from .db import db
from .models import User, Ticket, Transaction, Notification, PyObjectId

app = FastAPI(title="Directorate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simplified in-memory connections for WebSockets
connected_clients: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        connected_clients.remove(ws)

# Utility functions

def broadcast_event(event: str, payload: dict):
    for ws in connected_clients:
        ws.send_json({"event": event, "payload": payload})

# Users CRUD (simplified)
@app.post("/users", response_model=User)
def create_user(user: User):
    user_dict = user.dict(by_alias=True)
    res = db.users.insert_one(user_dict)
    user_dict["_id"] = res.inserted_id
    return User(**user_dict)

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str):
    data = db.users.find_one({"_id": PyObjectId(user_id)})
    if not data:
        raise HTTPException(status_code=404)
    return User(**data)

# Tickets
@app.post("/tickets", response_model=Ticket)
def create_ticket(ticket: Ticket):
    ticket_dict = ticket.dict(by_alias=True)
    res = db.tickets.insert_one(ticket_dict)
    ticket_dict["_id"] = res.inserted_id
    return Ticket(**ticket_dict)

@app.patch("/tickets/{ticket_id}/submit", response_model=Ticket)
def submit_ticket(ticket_id: str, ticket: Ticket):
    data = ticket.dict(exclude_unset=True, by_alias=True)
    db.tickets.update_one({"_id": PyObjectId(ticket_id)}, {"$set": data})
    new_data = db.tickets.find_one({"_id": PyObjectId(ticket_id)})
    return Ticket(**new_data)

@app.patch("/tickets/{ticket_id}/approve", response_model=Ticket)
def approve_ticket(ticket_id: str, credits: int = 0, pay: float = 0.0):
    update = {"status": "closed", "reward_credits": credits, "reward_pay": pay}
    db.tickets.update_one({"_id": PyObjectId(ticket_id)}, {"$set": update})
    db.transactions.insert_one({
        "user_id": db.tickets.find_one({"_id": PyObjectId(ticket_id)})["assignee_id"],
        "type": "payment",
        "amount_cr": credits,
        "amount_pay": pay,
        "related_ticket": PyObjectId(ticket_id),
        "approved_by": None,
    })
    new_data = db.tickets.find_one({"_id": PyObjectId(ticket_id)})
    broadcast_event("reward_granted", {"user_id": str(new_data["assignee_id"]), "credits": credits, "pay": pay, "ticket_id": ticket_id})
    return Ticket(**new_data)

@app.get("/transactions", response_model=List[Transaction])
def list_transactions(user_id: str):
    docs = list(db.transactions.find({"user_id": PyObjectId(user_id)}))
    return [Transaction(**d) for d in docs]
