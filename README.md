# Operations Management Portal

A public, sanitized copy of an internal operations workflow application built with Python, Flask, SQLite, HTML/CSS, and SMTP-based notifications.

## What It Does

- Manages PTO requests and approval workflows
- Supports shift swap submission and command review
- Parses overtime schedule uploads from Excel files
- Lets officers apply for overtime and supports command assignment/revocation
- Includes site-scoped visibility, audit history, notifications, and command notices
- Provides call list, calendar, user management, and account settings pages

## Stack

- Python
- Flask
- SQLite
- HTML/CSS
- openpyxl
- Git / GitHub

## Notes

- This repository is a cleaned public copy.
- Company-specific branding, site names, and building/location labels have been replaced with generic placeholders.
- Runtime data such as databases, uploaded files, and private credentials are not included.

## Local Run

1. Create and activate a virtual environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

## Intended Use

This project demonstrates workflow automation, role-based access, operational tooling, and internal web app development for scheduling and notification use cases.
