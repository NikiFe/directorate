# Directorate

This repository contains a small FastAPI application implementing parts of the
"Directorate of Order" platform as described in `directorate_ops_specification.md`.

## Running

Create a virtual environment and install the required packages:

```
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pymongo python-socketio passlib[bcrypt]
```

Run the API with:

```
uvicorn backend.api:app --reload
```

A local MongoDB instance is expected at `mongodb://localhost:27017/directorate`.
Open `http://localhost:8000/static/` in your browser to view the front-end.
