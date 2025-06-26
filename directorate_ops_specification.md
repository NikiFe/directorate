# FILE: directorate_ops_specification.md  
**Revision v2.0 — 2025-06-26**  

---

## 0 Executive Overview  
This local-hosted web platform simulates the Directorate of Order:  

* Hierarchical user accounts (**asset → shadow → marshal → executor → Nyx → Niki**).  
* Multi-category ticketing / task workflow with escalation.  
* Real-time notifications via WebSockets.  
* Embedded **Nyx** AI (Gemini 2.5 Flash) for automated directives.  
* Hidden super-authority **Controller Niki** (ID 7360) able to override any rule while remaining invisible.  
* **Integrated social-credit & monetary economy** — each completed task yields credits/pay after superior approval; abnormally high awards are auto-escalated to prevent corruption.

Everything runs on one machine; MongoDB provides persistence.

---

## 1 Technology Stack  

| Layer | Choice | Reason |
|-------|--------|--------|
| Back-end | Python 3.11 + FastAPI | Async, type-hints, WebSockets, auto OpenAPI. |
| AI Driver | `google-genai` SDK (Gemini 2.5 Flash) | Meets spec, fast local calls. |
| Database | MongoDB (local) | Flexible for nested structures & ledgers. |
| Real-time | FastAPI WebSockets + `python-socketio` | Lightweight, no broker. |
| Auth | FastAPI-Users (bcrypt + JWT) | Provides roles & refresh tokens. |
| Front-end | Any SPA; served from `/static`. |
| Theme | Brutalist monochrome (black / grey, crimson for Nyx). |

---

## 2 Domain Model (MongoDB Collections)

### 2.1 `users`
```

\_id          ObjectId
username     string
email        string
password\_hash string
rank         "asset"|"shadow"|"marshal"|"executor"|"nyx"|"niki"
reports\_to   ObjectId (nullable)
hidden       bool  (true only for rank "niki")
credits      int   (social credit score)
balance      decimal128  (currency units)
created\_at   datetime
updated\_at   datetime

```

### 2.2 `tickets`
```

\_id            ObjectId
title          string
body\_md        string
category       string   # see §4
sub\_category   string   # see §4
status         "open"|"in\_progress"|"awaiting\_review"|"closed"
visibility     "private"|"hierarchical"
author\_id      ObjectId
assignee\_id    ObjectId
target\_rank    string
watchers       \[ObjectId]
reward\_credits int      # proposed by author or AI
reward\_pay     decimal128
approval\_log   \[ {approver\_id, credits, pay, ts} ]
created\_at     datetime
updated\_at     datetime

```

### 2.3 `transactions`
```

\_id        ObjectId
user\_id    ObjectId
type       "credit\_award"|"payment"|"manual\_adj"
amount\_cr  int
amount\_pay decimal128
related\_ticket ObjectId (nullable)
approved\_by ObjectId
ts         datetime

```

### 2.4 `notifications`
```

\_id        ObjectId
user\_id    ObjectId
message    string
ticket\_id  ObjectId (nullable)
read       bool
ts         datetime

```

---

## 3 Hierarchy & Permission Matrix  

| Action | Asset | Shadow | Marshal | Executor | Nyx | Niki |
|--------|-------|--------|---------|----------|-----|------|
| View self tickets | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| View subordinates tickets | ✖ | ✔ (assets) | ✔ (≤shadow) | ✔ (≤marshal) | ✔ | ✔ |
| Create ticket upward | ✔ | ✔ | ✔ | ✔ | — | — |
| Submit reward proposal | ✔ | ✔ | ✔ | ✔ | — | — |
| Approve normal reward | ✖ | ✖ | ✔ (assets, shadows) | ✔ (≤marshal) | ✔ | ✔ |
| Escalation approval | ✖ | ✖ | ✖ | ✔ (≤executor) | ✔ | ✔ |
| Approve promotion | ✖ | ✖ | ✔ (assets, shadows) | ✔ (≤marshal) | ✔ | ✔ |
| Broadcast command | ✖ | ✖ | ✖ | ✔ | ✔ | ✔ |
| Hidden override | ✖ | ✖ | ✖ | ✖ | ✖ | ✔ |

---

## 4 Ticket Categories & Sub-Categories  

| Category | Sub-categories |
|----------|----------------|
| **Order** | Routine Directive · Special Operation · Resource Allocation |
| **Incident** | Security Breach · Civil Unrest · Technical Failure · Health Hazard |
| **Personnel** | Promotion Request · Demotion Request · Disciplinary · Commendation |
| **Intel** | Recon Report · Data Leak · Counter-Espionage · Asset Status |
| **Logistics** | Supply Shortage · Transport · Maintenance · Infrastructure |
| **Request** | Resource · Leave · Clarification · Support |
| **Audit** | Compliance Review · Process Check · System Integrity |
| **Economy** | Credit Dispute · Payment Inquiry |
| **Miscellaneous** | Other |

---

## 5 Economy & Social Credit Logic  

1. **Base Pay & Credit Rates**  
   | Rank | Base Hourly Pay | Base Credit per Task |
   |------|-----------------|----------------------|
   | Asset | ¤3.0 | 1 |
   | Shadow | ¤4.5 | 2 |
   | Marshal | ¤6.0 | 3 |
   | Executor | ¤8.0 | 4 |
   | Nyx | configurable | — |

2. **Task Reward Flow**  
   1. Author or AI proposes `reward_credits` and `reward_pay` when setting ticket status → `awaiting_review`.  
   2. Direct superior reviews; may adjust.  
   3. If `reward_credits` > 100 **OR** `reward_pay` > 5×base-pay of assignee, ticket auto-escalates to next superior rank.  
   4. On approval, **transactions** record is created; user `credits` and `balance` update atomically.  
   5. Closed ticket becomes read-only.  

---

## 6 API Contract (Selective)  

### 6.1 Tickets / Rewards  
| Method | Path | Description |
|--------|------|-------------|
| POST | `/tickets` | create ticket (status `open`) |
| PATCH | `/tickets/{id}/submit` | submit for review, include proposed `reward_credits`, `reward_pay` |
| PATCH | `/tickets/{id}/approve` | approver sets final rewards, changes status to `closed` or escalates |
| POST | `/tickets/{id}/comment` | add thread comment |

### 6.2 Transactions  
| Method | Path | Description |
|--------|------|-------------|
| GET | `/transactions` | list own ledger (admins can filter by user) |

### 6.3 Economy Admin  
| Method | Path | Description |
|--------|------|-------------|
| PATCH | `/users/{id}/adjust` | manual credit/pay correction (marshal+ for subordinates) |

Hidden Niki route `/niki/command` accepts economy actions identical to Nyx JSON schema.

---

## 7 WebSocket Events  

* `reward_granted` — `{user_id, credits, pay, ticket_id}`  
* `credits_update` — `{user_id, new_credits}`  

---

## 8 Nyx & Niki AI Integration  

* **Nyx Prompt Addendum**  
  > You can propose rewards via JSON:  
  > `{"action":"create_ticket","data":{...,"reward_credits":X,"reward_pay":Y}}`  
  > or `{"action":"approve_rewards","ticket_id": "...", "credits": X, "pay": Y}`  

* **Auto-Escalation** is enforced server-side; Nyx cannot override. Niki can via hidden endpoint.  

---

## 9 Front-End UI Additions  

* Wallet widget (top-right) shows `credits` and `balance` with triangle rank icon.  
* Ticket form includes reward proposal inputs (visible once work finished).  
* Review panel for superiors: approve / adjust / escalate buttons.  
* Ledger page: paginated list of credit & pay transactions.  

---

## 10 Deployment Steps  

1. Install MongoDB locally (`mongodb://localhost:27017/directorate`).  
2. `python -m venv venv && source venv/bin/activate && pip install fastapi uvicorn pymongo python-socketio google-genai fastapi-users`  
3. `.env` file with:  
```

MONGO\_URI=mongodb://localhost:27017/directorate
GEMINI\_API\_KEY=\<your\_key>
JWT\_SECRET=<random>

```
4. `uvicorn api:app --reload`.  
5. Build front-end SPA → copy to `backend/static/`.  

---

## 11 Future Enhancements  

* GridFS for file attachments.  
* Scheduled credit decay or salary payout cron.  
* Analytical dashboard for economy trends and credit distribution.  
