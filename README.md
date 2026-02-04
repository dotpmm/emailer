# [Emailer v4](https://emailer-v3-api.onrender.com)

![Fernet](https://img.shields.io/badge/Fernet-AES--128-blue)
![SHA-256](https://img.shields.io/badge/SHA--256-Hashing-green)
![SMTP](https://img.shields.io/badge/SMTP-SSL-orange)
![Gmail](https://img.shields.io/badge/Gmail-Compatible-red)



## Features

- Multiple recepients
- Repeat 
- `html` support in body
- `Cc` `Bcc` `Reply-to` everything supported

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard with lifetime metrics |
| `/auth` | POST | Authenticate with SMTP credentials, get token |
| `/send` | POST | Send email(s) with optional repeat |

## Usage

### 1. Get a Gmail App Password

> [!IMPORTANT]
> You **must** use an App Password, not your regular Gmail password.

1. Go to your [Google Account](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll down to **App passwords** or visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Select **Mail** and give it a name, then click **Generate**
5. Copy the 16-character password (spaces don't matter)
6. That's your app password which you need to use.
### 2. Authenticate

```bash
curl -X POST https://your-api.com/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"you@gmail.com","password":"xxxx xxxx xxxx xxxx"}'
```

Response:
```json
{"token": "abc123...", "expires_in_hours": 1, "message": "..."}
```

### 3. Send Email(s)

```bash
# Single recipient
curl -X POST https://your-api.com/send \
  -H "Content-Type: application/json" \
  -H "X-Token: abc123..." \
  -d '{"recipients":"target@example.com","subject":"Hello","body":"Hi there!"}'

# Multiple recipients with HTML
curl -X POST https://your-api.com/send \
  -H "Content-Type: application/json" \
  -H "X-Token: abc123..." \
  -d '{
    "recipients": ["a@b.com", "c@d.com"],
    "subject": "Newsletter",
    "body": "<h1>Hello!</h1><p>Welcome aboard.</p>",
    "is_html": true
  }'
```

## Security

- Credentials encrypted at rest (Fernet/AES) : Go check the code, i have explained in detail!
- Tokens expire after 1 hour
