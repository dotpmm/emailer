from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
import smtplib
from email.message import EmailMessage
import uuid

app = FastAPI()

# In-memory store for tokens and credentials (for demo only)
auth_tokens = {}

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    message: str
    sender_email: EmailStr = None
    token: str = None

class MailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    quantity: int
    token: str

@app.post("/auth", response_model=AuthResponse)
async def auth(request: AuthRequest):
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(request.email, request.password)
        token = str(uuid.uuid4())
        auth_tokens[token] = {"email": request.email, "password": request.password}
        return AuthResponse(message="Authentication successful", sender_email=request.email, token=token)
    except smtplib.SMTPAuthenticationError:
        return AuthResponse(message="Authentication failed")

@app.post("/mail")
async def mail(request: MailRequest):
    creds = auth_tokens.get(request.token)
    if not creds:
        return {"message": "Invalid or expired token"}
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(creds["email"], creds["password"])
            msg = EmailMessage()
            msg['Subject'] = request.subject
            msg['From'] = creds["email"]
            msg['To'] = request.recipient_email
            msg.set_content(request.body)
            for _ in range(request.quantity):
                smtp.send_message(msg)
        return {"message": "Success"}
    except Exception as e:
        return {"message": f"Failed to send email: {str(e)}"}
