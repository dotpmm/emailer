# Emailer v3

A lightweight command-line utility for sending emails via Gmail SMTP. The tool supports batch delivery to multiple recipients or repeated delivery to a single recipient, enabling quick outbound communication workflows. 


![Project Status](https://img.shields.io/badge/status-active-brightgreen)
![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.13+-yellow)
![SMTP](https://img.shields.io/badge/SMTP-Gmail-red)

## Features

* Gmail SMTP over SSL (port 465)
* Supports:

  * One message to many recipients
  * Many messages to a single recipient
* Environment-driven credential management via `.env` variables
* Minimal dependencies; Python 3.13+ runtime 

## Requirements

* Python 3.13 or later
* Gmail account with App Password enabled
* `.env` file containing:

  ```
  EMAIL_USER=your_email@gmail.com
  EMAIL_PASS=your_app_password
  ```

## Installation

```
uv sync
```

(Or install with pip if preferred.)

## Usage

Run the CLI:

```
uv run main.py
```

## Notes

* `imghdr` support is commented out because the module is deprecated as of 2025.
* Gmail may require enabling App Passwords if 2FA is active.

