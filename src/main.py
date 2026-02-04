import os
import time
import secrets
import smtplib
import logging
import hashlib
from typing import Optional, Union
from datetime import datetime, timedelta
from email.message import EmailMessage
from contextlib import asynccontextmanager

from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator
from motor.motor_asyncio import AsyncIOMotorClient

# logger
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
log = logging.getLogger(__name__)

# SHA KEY, lives in ram...so no risk!
FERNET_KEY = Fernet.generate_key()
_cipher = Fernet(FERNET_KEY)
_tokens: dict[str, dict] = {}
TOKEN_EXPIRY_HOURS = 1

MONGO_URI = os.getenv("MONGO_URI", "")
_db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    if MONGO_URI:
        try:
            client = AsyncIOMotorClient(MONGO_URI)
            _db = client.emailer
            await _db.metrics.update_one(
                {"_id": "stats"},
                {"$setOnInsert": {"emails_sent": 0, "tokens_issued": 0}},
                upsert=True
            )
            log.info("MongoDB connected")
        except Exception as e:
            log.error(f"MongoDB connection failed: {e}")
            _db = None
    else:
        log.warning("MONGO_URI not found!")
    yield

# simple hasher
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# for the 1hr expiration logic, i tried other cozy shi, but they gave some errors! so i reverted :sob:
def _cleanup_expired_tokens():
    now = datetime.now()
    expired = [t for t, data in _tokens.items() if data["expires_at"] < now]
    for t in expired:
        del _tokens[t]

# for email and app password storage
def _encrypt(data: str) -> bytes:
    return _cipher.encrypt(data.encode())

# hehehe, use ur brain!
def _decrypt(data: bytes) -> str:
    return _cipher.decrypt(data).decode()

# mongo method
async def increment_metric(field: str, amount: int = 1):
    if _db is not None:
        try:
            await _db.metrics.update_one(
                {"_id": "stats"},
                {"$inc": {field: amount}}
            )
        except Exception as e:
            log.error(f"Failed to update metric {field}: {e}")

# for / endpoint
async def get_metrics() -> dict:
    if _db is not None:
        try:
            doc = await _db.metrics.find_one({"_id": "stats"})
            if doc:
                return {
                    "emails_sent": doc.get("emails_sent", 0),
                    "tokens_issued": doc.get("tokens_issued", 0)
                }
        except Exception as e:
            log.error(f"Failed to get metrics: {e}")
    return {"emails_sent": 0, "tokens_issued": 0}

# Learnt this for askbookie, so wanted to try pydantic by myself...might feel unnecessary..but i was excited lmao!
class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=465)


class AuthResponse(BaseModel):
    token: str
    expires_in_hours: int
    message: str


class SendRequest(BaseModel):
    recipients: Union[EmailStr, list[EmailStr]]
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1)
    repeat_count: int = Field(default=1, ge=1, le=50)
    is_html: bool = Field(default=False, description="Send as HTML email")
    cc: Optional[list[EmailStr]] = Field(default=None, description="CC recipients")
    bcc: Optional[list[EmailStr]] = Field(default=None, description="BCC recipients")
    reply_to: Optional[EmailStr] = Field(default=None, description="Reply-to address")

    @field_validator("recipients", mode="before")
    @classmethod
    def normalize_recipients(cls, v):
        if isinstance(v, str):
            return [v]
        return v

class SendResponse(BaseModel):
    sent: int
    failed: int
    success: bool
    message: str

def get_smtp_creds(token: str) -> dict:
    # had forgotten, later added! 
    _cleanup_expired_tokens()

    token_hash = _hash_token(token)
    
    if token_hash not in _tokens:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token. Use /auth first."
        )
    
    data = _tokens[token_hash]
    if data["expires_at"] < datetime.now():
        del _tokens[token_hash]
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired. Re-authenticate.")
    
    return {
        "email": _decrypt(data["email"]),
        "password": _decrypt(data["password"]),
        "smtp_host": data["smtp_host"],
        "smtp_port": data["smtp_port"],
    }

# hehe, pydantic
def send_email(
    creds: dict,
    to: str,
    subject: str,
    body: str,
    is_html: bool = False,
    cc: list[str] = None,
    bcc: list[str] = None,
    reply_to: str = None
) -> None:
    msg = EmailMessage()
    msg["From"] = creds["email"]
    msg["To"] = to
    msg["Subject"] = subject
    
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = reply_to
        
    # this was in the docs of smtp, so just added...its good if u wanna add images and docs
    msg.set_content(body, subtype="html" if is_html else "plain")
    
    all_recipients = [to] + (cc or []) + (bcc or [])
    
    with smtplib.SMTP_SSL(creds["smtp_host"], creds["smtp_port"], timeout=30) as smtp:
        smtp.login(creds["email"], creds["password"])
        smtp.send_message(msg, to_addrs=all_recipients)
    
    log.info(f"Email sent to {to}")

# should i make an assets folder and make index.html?. ah fk it, me lazy
def get_dashboard_html(metrics: dict, active_tokens: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emailer v4</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #000000;
            color: #fafafa;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .status {{
            position: fixed;
            top: 20px;
            right: 20px;
        }}
        .status-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        .status-text {{
            color: #71717a;
            font-size: 13px;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .container {{
            max-width: 480px;
            width: 100%;
        }}
        .header {{
            text-align: center;
            margin-bottom: 32px;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
        }}
        .header p {{
            color: #71717a;
            font-size: 14px;
        }}
        .cards {{
            display: grid;
            gap: 16px;
        }}
        .card {{
            background: #0a0a0a;
            border: 1px solid #000000;
            border-radius: 12px;
            padding: 24px;
            transition: border-color 0.2s;
        }}
        .card:hover {{
            border-color: #ffffff;
        }}
        .card-label {{
            font-size: 13px;
            color: #71717a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 36px;
            font-weight: 600;
            letter-spacing: -1px;
        }}
        .card-value.highlight {{
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .footer {{
            margin-top: 24px;
            text-align: center;
        }}
        .footer a {{
            color: #71717a;
            font-size: 13px;
            text-decoration: none;
            transition: color 0.2s;
        }}
        .footer a:hover {{
            color: #fafafa;
        }}
    </style>
</head>
<body>
    <div class="status">
        <span class="status-dot"></span>
        <span class="status-text">{"MongoDB Connected" if _db is not None else "Metrics Disabled"}</span>
    </div>
    <div class="container">
        <div class="header">
            <h1>Emailer v4</h1>
            <p>Minimal and secure token-based emailer API. Auth once, send many!</p>
        </div>
        <div class="cards">
            <div class="card">
                <div class="card-label">Emails Sent</div>
                <div class="card-value highlight">{metrics['emails_sent']:,}</div>
            </div>
            <div class="card">
                <div class="card-label">Tokens Issued</div>
                <div class="card-value">{metrics['tokens_issued']:,}</div>
            </div>
            <div class="card">
                <div class="card-label">Active Sessions</div>
                <div class="card-value">{active_tokens}</div>
            </div>
        </div>
        <div class="footer">
            <a href="/docs">Sorry, i didn't make a frontend for this, so please use the Swagger UI →</a>
        </div>
    </div>
</body>
</html>"""


app = FastAPI(
    title="Emailer",
    version="4.0.0",
    description="Minimal, secure token-based email API. Auth once, send many!",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ladies and mentelgen...enjoyy!!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/", response_class=HTMLResponse)
async def root():
    metrics = await get_metrics()
    _cleanup_expired_tokens()
    return get_dashboard_html(metrics, len(_tokens))


@app.get("/iamalive")
def health():
    return {"status": "ok"}


@app.post("/auth", response_model=AuthResponse)
async def authenticate(req: AuthRequest):
    """
        You are here to get an authentication token.
        Follow the steps below :)

        **Steps:**
        - App password: You **must** use an App Password, not your regular Gmail password.

        1. Go to your [Google Account](https://myaccount.google.com/)
        2. Navigate to **Security** → **2-Step Verification** (enable it if not already enabled)
        3. Scroll down to **App passwords** or visit https://myaccount.google.com/apppasswords
        4. Select **Mail**, give it a name, then click **Generate**
        5. Copy the 16-character password (spaces don’t matter)
        6. This is the app password you need to use
        7. **PLEASE COPY IT**
        8. Submit your Gmail address and App Password (the 16-character code you copied) to the `/auth` endpoint
        9. The server will validate the credentials
        10. It returns a `token` valid for 1 hour
        11. **AGAIN, PLEASE COPY IT** :)
    """

    email_str = str(req.email)
    password_str = str(req.password)
    
    log.info(f"Auth attempt for {email_str}")
    
    try:
        with smtplib.SMTP_SSL(req.smtp_host, req.smtp_port, timeout=15) as smtp:
            smtp.login(email_str, password_str)
            log.info(f"SMTP auth successful for {email_str}")
    except smtplib.SMTPAuthenticationError as e:
        log.error(f"SMTP auth failed for {email_str}: {e}")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password. For Gmail, use an App Password."
        )
    except smtplib.SMTPException as e:
        log.error(f"SMTP error for {email_str}: {e}")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"SMTP connection failed: {str(e)}"
        )
    except Exception as e:
        log.error(f"Unexpected error for {email_str}: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Connection error: {str(e)}"
        )
    
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    
    _tokens[token_hash] = {
        "email": _encrypt(email_str),
        "password": _encrypt(password_str),
        "smtp_host": req.smtp_host,
        "smtp_port": req.smtp_port,
        "created_at": datetime.now(),
        "expires_at": expires,
    }
    
    await increment_metric("tokens_issued")
    
    log.info(f"Token issued for {email_str} (expires in {TOKEN_EXPIRY_HOURS}h)")
    
    return AuthResponse(
        token=token,
        expires_in_hours=TOKEN_EXPIRY_HOURS,
        message="Authentication successful. Use this token in X-Token header."
    )


@app.post("/send", response_model=SendResponse)
async def send(req: SendRequest, x_token: str = Header(..., alias="X-Token")):
    """
    If you are here after authenticating yourself from the `/auth` endpoint, GG!
    Hope you have the token ready to paste :)

    Now:

    - Paste the token in the `X-Token` field and proceed with your email request.
    - Be patient until all emails are fully sent.

    Thank you for using this!
    pmmdot! :)
    """
    
    creds = get_smtp_creds(x_token)
    
    sent = 0
    failed = 0
    recipients = req.recipients if isinstance(req.recipients, list) else [req.recipients]
    
    cc_list = [str(e) for e in req.cc] if req.cc else None
    bcc_list = [str(e) for e in req.bcc] if req.bcc else None
    reply_to_str = str(req.reply_to) if req.reply_to else None
    
    log.info(f"Sending to {len(recipients)} recipient(s), repeat={req.repeat_count}")
    
    for recipient in recipients:
        for i in range(req.repeat_count):
            try:
                send_email(
                    creds,
                    str(recipient),
                    req.subject,
                    req.body,
                    is_html=req.is_html,
                    cc=cc_list,
                    bcc=bcc_list,
                    reply_to=reply_to_str
                )
                sent += 1
            except smtplib.SMTPAuthenticationError as e:
                log.error(f"Auth failed during send: {e}")
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    "SMTP authentication failed. Your token may be invalid."
                )
            except Exception as e:
                log.error(f"Failed [{i+1}/{req.repeat_count}] to {recipient}: {e}")
                failed += 1
            
            if i < req.repeat_count - 1 or recipient != recipients[-1]:
                time.sleep(1)
    
    if sent > 0:
        await increment_metric("emails_sent", sent)
    
    total = sent + failed
    return SendResponse(
        sent=sent,
        failed=failed,
        success=failed == 0,
        message=f"Sent {sent}/{total} emails successfully."
    )
