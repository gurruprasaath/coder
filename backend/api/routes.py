from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import MetaData, Table, insert, select, update, delete

from schemas.generate import GenerateRequest
from logger import setup_logger
from pipeline.orchestrator import run_pipeline, get_evaluation_logs
from db import get_db
import models

logger = setup_logger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# GENERATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_endpoint(request: GenerateRequest):
    logger.info(f"Received generation request: {request.prompt}")
    try:
        result = run_pipeline(request.prompt)

        if result["config"] is None and not result.get("needs_clarification"):
            raise Exception(result["logs"][-1] if result["logs"] else "Pipeline failed")

        return result
    except Exception as e:
        logger.error(f"Generation pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eval-metrics")
async def eval_metrics_endpoint():
    """Return all evaluation logs and a computed summary."""
    return get_evaluation_logs()


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ENDPOINTS (DB-backed, app_id isolated)
# ─────────────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/users/register")
async def register(request: RegisterRequest, req: Request, db: Session = Depends(get_db)):
    app_id = req.headers.get("x-app-id", "default")
    existing = db.query(models.User).filter(
        models.User.username == request.username,
        models.User.app_id == app_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = models.User(
        username=request.username,
        password=request.password,
        role="user",
        app_id=app_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}


@router.post("/login")
async def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    app_id = req.headers.get("x-app-id", "default")
    user = db.query(models.User).filter(
        models.User.username == request.username,
        models.User.app_id == app_id
    ).first()

    if user:
        if user.password == request.password:
            return {"id": user.id, "username": user.username, "role": user.role}
        raise HTTPException(status_code=401, detail="Invalid password")

    # Fallback: allow login for any user not yet registered (demo mode)
    return {"id": 99, "username": request.username, "role": "User"}


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC CRUD ENDPOINTS  (table-generic, app_id isolated)
# ─────────────────────────────────────────────────────────────────────────────

dynamic_metadata = MetaData()


def get_dynamic_table(db: Session, table_name: str) -> Table:
    """Reflect the requested table from the live SQLite engine."""
    try:
        dynamic_metadata.reflect(bind=db.get_bind(), only=[table_name])
    except Exception:
        pass

    if table_name not in dynamic_metadata.tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist.")
    return dynamic_metadata.tables[table_name]


def validate_payload(table: Table, payload: dict, is_update: bool = False):
    valid_cols = [c.name for c in table.columns]
    bad = [k for k in payload if k not in valid_cols]
    if bad:
        raise HTTPException(status_code=400, detail=f"Invalid fields for '{table.name}': {bad}")
        
    if not is_update:
        missing = []
        for c in table.columns:
            # If column is required, not a PK, has no default, and isn't our internal app_id
            if not c.nullable and not c.primary_key and c.default is None and c.server_default is None:
                if c.name not in payload and c.name != "app_id":
                    missing.append(c.name)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields for '{table.name}': {missing}")


@router.post("/data/{table_name}")
async def dynamic_insert(table_name: str, request: Request, db: Session = Depends(get_db)):
    app_id = request.headers.get("x-app-id")
    if not app_id:
        raise HTTPException(status_code=400, detail="Missing X-App-Id header")

    table   = get_dynamic_table(db, table_name)
    payload = await request.json()
    payload["app_id"] = app_id
    validate_payload(table, payload)

    try:
        result = db.execute(insert(table).values(**payload))
        db.commit()
        return {"success": True, "message": f"Inserted into {table_name}", "id": result.lastrowid}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/data/{table_name}")
async def dynamic_get(table_name: str, request: Request, db: Session = Depends(get_db)):
    app_id = request.headers.get("x-app-id")
    if not app_id:
        raise HTTPException(status_code=400, detail="Missing X-App-Id header")

    table = get_dynamic_table(db, table_name)
    try:
        rows = db.execute(select(table).where(table.c.app_id == app_id)).all()
        return {"success": True, "data": [dict(r._mapping) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/data/{table_name}/{id}")
async def dynamic_update(table_name: str, id: int, request: Request, db: Session = Depends(get_db)):
    app_id = request.headers.get("x-app-id")
    if not app_id:
        raise HTTPException(status_code=400, detail="Missing X-App-Id header")

    table   = get_dynamic_table(db, table_name)
    payload = await request.json()
    validate_payload(table, payload, is_update=True)

    if "id" not in [c.name for c in table.columns]:
        raise HTTPException(status_code=400, detail=f"No 'id' column in {table_name}.")

    try:
        result = db.execute(
            update(table)
            .where(table.c.id == id)
            .where(table.c.app_id == app_id)
            .values(**payload)
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found or unauthorized")
        return {"success": True, "message": "Updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/data/{table_name}/{id}")
async def dynamic_delete(table_name: str, id: int, request: Request, db: Session = Depends(get_db)):
    app_id = request.headers.get("x-app-id")
    if not app_id:
        raise HTTPException(status_code=400, detail="Missing X-App-Id header")

    table = get_dynamic_table(db, table_name)

    if "id" not in [c.name for c in table.columns]:
        raise HTTPException(status_code=400, detail=f"No 'id' column in {table_name}.")

    try:
        result = db.execute(
            delete(table)
            .where(table.c.id == id)
            .where(table.c.app_id == app_id)
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found or unauthorized")
        return {"success": True, "message": "Deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
