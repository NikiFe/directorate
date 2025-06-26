from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
from fastapi.staticfiles import StaticFiles
from typing import List
from datetime import datetime
import asyncio

from .db import db
from .models import User, Ticket, Transaction, Notification, PyObjectId

app = FastAPI(title="Directorate API")

app.mount("/static", StaticFiles(directory="backend/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simplified in-memory connections for WebSockets
connected_clients: List[WebSocket] = []

# Rank hierarchy and base pay used for reward escalation logic
RANKS = ["asset", "shadow", "marshal", "executor", "nyx", "niki"]
BASE_PAY = {
    "asset": 3.0,
    "shadow": 4.5,
    "marshal": 6.0,
    "executor": 8.0,
    "nyx": 0.0,
    "niki": 0.0,
}


def next_rank(rank: str) -> str:
    try:
        idx = RANKS.index(rank)
    except ValueError:
        return rank
    return RANKS[idx + 1] if idx + 1 < len(RANKS) else rank

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

async def broadcast_event(event: str, payload: dict):
    for ws in connected_clients:
        try:
            await ws.send_json({"event": event, "payload": payload})
        except Exception:
            pass

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


@app.patch("/users/{user_id}/adjust", response_model=User)
def adjust_user(user_id: str, credits: int = 0, pay: float = 0.0):
    db.users.update_one({"_id": PyObjectId(user_id)}, {"$inc": {"credits": credits, "balance": pay}})
    db.transactions.insert_one(
        {
            "user_id": PyObjectId(user_id),
            "type": "manual_adj",
            "amount_cr": credits,
            "amount_pay": pay,
            "related_ticket": None,
            "approved_by": None,
            "ts": datetime.utcnow(),
        }
    )
    user_data = db.users.find_one({"_id": PyObjectId(user_id)})
    asyncio.create_task(broadcast_event("credits_update", {"user_id": user_id, "new_credits": user_data["credits"]}))
    return User(**user_data)

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
    data["status"] = "awaiting_review"
    db.tickets.update_one({"_id": PyObjectId(ticket_id)}, {"$set": data})
    new_data = db.tickets.find_one({"_id": PyObjectId(ticket_id)})
    return Ticket(**new_data)

@app.patch("/tickets/{ticket_id}/approve", response_model=Ticket)
def approve_ticket(ticket_id: str, credits: int = 0, pay: float = 0.0):
    ticket = db.tickets.find_one({"_id": PyObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404)

    assignee = db.users.find_one({"_id": ticket["assignee_id"]})
    base_pay = BASE_PAY.get(assignee.get("rank", "asset"), 0.0)

    # Determine if escalation is required
    if credits > 100 or pay > base_pay * 5:
        next_target = next_rank(ticket.get("target_rank", assignee["rank"]))
        db.tickets.update_one(
            {"_id": PyObjectId(ticket_id)},
            {"$set": {"status": "awaiting_review", "target_rank": next_target}},
        )
        return Ticket(**db.tickets.find_one({"_id": PyObjectId(ticket_id)}))

    # Final approval path
    update = {
        "status": "closed",
        "reward_credits": credits,
        "reward_pay": pay,
        "approval_log": ticket.get("approval_log", [])
        + [{"approver_id": None, "credits": credits, "pay": pay, "ts": datetime.utcnow()}],
    }
    db.tickets.update_one({"_id": PyObjectId(ticket_id)}, {"$set": update})

    db.transactions.insert_one(
        {
            "user_id": ticket["assignee_id"],
            "type": "payment",
            "amount_cr": credits,
            "amount_pay": pay,
            "related_ticket": PyObjectId(ticket_id),
            "approved_by": None,
        }
    )

    db.users.update_one(
        {"_id": ticket["assignee_id"]},
        {"$inc": {"credits": credits, "balance": pay}},
    )

    new_user = db.users.find_one({"_id": ticket["assignee_id"]})
    asyncio.create_task(
        broadcast_event(
            "reward_granted",
            {"user_id": str(ticket["assignee_id"]), "credits": credits, "pay": pay, "ticket_id": ticket_id},
        )
    )
    asyncio.create_task(
        broadcast_event(
            "credits_update", {"user_id": str(ticket["assignee_id"]), "new_credits": new_user["credits"]}
        )
    )

    return Ticket(**db.tickets.find_one({"_id": PyObjectId(ticket_id)}))

@app.get("/transactions", response_model=List[Transaction])
def list_transactions(user_id: str):
    docs = list(db.transactions.find({"user_id": PyObjectId(user_id)}))
    return [Transaction(**d) for d in docs]

# Ticket comments
@app.post("/tickets/{ticket_id}/comment", response_model=Ticket)
def comment_ticket(ticket_id: str, body: str = Body(...), author_id: str = Body(...)):
    ticket = db.tickets.find_one({"_id": PyObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404)
    comment = {"author_id": PyObjectId(author_id), "body": body, "ts": datetime.utcnow()}
    db.tickets.update_one({"_id": PyObjectId(ticket_id)}, {"$push": {"comments": comment}})
    return Ticket(**db.tickets.find_one({"_id": PyObjectId(ticket_id)}))

# Notifications endpoints
@app.get("/notifications", response_model=List[Notification])
def list_notifications(user_id: str):
    docs = list(db.notifications.find({"user_id": PyObjectId(user_id)}).sort("ts", -1))
    return [Notification(**d) for d in docs]

@app.post("/notifications", response_model=Notification)
def create_notification(notification: Notification):
    data = notification.dict(by_alias=True)
    res = db.notifications.insert_one(data)
    data["_id"] = res.inserted_id
    asyncio.create_task(broadcast_event("notify", {"user_id": str(data["user_id"]), "message": data["message"]}))
    return Notification(**data)
