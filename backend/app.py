import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from .db import init_db, add_user, get_user, update_user, remove_user
from .verify import generate_code, verify_code
from .email_sender import send_verification_email

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

allowed_freq = {"monthly", "weekly", "holiday"}
allowed_salutation = {"哥哥", "姐姐"}


class VerifySendRequest(BaseModel):
    email: EmailStr
    action: str


class SubscribeRequest(BaseModel):
    email: EmailStr
    frequency: str
    salutation: str
    birthday: str | None = None
    code: str


class UnsubscribeRequest(BaseModel):
    email: EmailStr
    code: str


class UpdateRequest(BaseModel):
    email: EmailStr
    frequency: str | None = None
    salutation: str | None = None
    birthday: str | None = None
    code: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/verify/send")
def verify_send(req: VerifySendRequest):
    if req.action not in {"subscribe", "unsubscribe", "update"}:
        raise HTTPException(status_code=400, detail="invalid action")
    code = generate_code(req.email, req.action)
    send_verification_email(req.email, code, req.action)
    return {"ok": True}


@app.post("/subscribe")
def subscribe(req: SubscribeRequest):
    if req.frequency not in allowed_freq:
        raise HTTPException(status_code=400, detail="invalid frequency")
    if req.salutation not in allowed_salutation:
        raise HTTPException(status_code=400, detail="invalid salutation")
    if not verify_code(req.email, "subscribe", req.code):
        raise HTTPException(status_code=400, detail="invalid code")
    if get_user(req.email):
        raise HTTPException(status_code=400, detail="already subscribed")
    add_user(req.email, req.frequency, req.salutation, req.birthday)
    return {"ok": True}


@app.post("/unsubscribe")
def unsubscribe(req: UnsubscribeRequest):
    if not verify_code(req.email, "unsubscribe", req.code):
        raise HTTPException(status_code=400, detail="invalid code")
    if not get_user(req.email):
        raise HTTPException(status_code=400, detail="not subscribed")
    remove_user(req.email)
    return {"ok": True}


@app.post("/update")
def update(req: UpdateRequest):
    if not verify_code(req.email, "update", req.code):
        raise HTTPException(status_code=400, detail="invalid code")
    current = get_user(req.email)
    if not current:
        raise HTTPException(status_code=400, detail="not subscribed")
    new_frequency = current["frequency"]
    new_salutation = current["salutation"]
    new_birthday = current["birthday"]
    if req.frequency is not None:
        if req.frequency not in allowed_freq:
            raise HTTPException(status_code=400, detail="invalid frequency")
        new_frequency = req.frequency
    if req.salutation is not None:
        if req.salutation not in allowed_salutation:
            raise HTTPException(status_code=400, detail="invalid salutation")
        new_salutation = req.salutation
    if req.birthday is not None:
        new_birthday = req.birthday
    update_user(req.email, new_frequency, new_salutation, new_birthday)
    return {"ok": True}
