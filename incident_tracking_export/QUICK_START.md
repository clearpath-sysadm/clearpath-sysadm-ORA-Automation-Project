# ⚡ Quick Start - 5 Minutes to Running System

This is the fastest path to get the incident tracking system running.

## Prerequisites Check
```bash
# Check Python
python --version  # Need 3.7+

# Check PostgreSQL
psql --version    # Need 9.5+

# Check pip
pip --version
```

## Installation (Copy & Paste)

### 1️⃣ Database (30 seconds)
```bash
# Create database (if needed)
createdb incident_tracker

# Run schema
psql incident_tracker < database_schema.sql

# Verify
psql incident_tracker -c "SELECT COUNT(*) FROM production_incidents;"
```

### 2️⃣ Backend (2 minutes)

Create `app.py`:
```python
from flask import Flask, request, jsonify, Response, render_template
import mimetypes
import psycopg2
import os

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(
        database="incident_tracker",
        user="your_username",
        password="your_password",
        host="localhost"
    )

# PASTE ALL ROUTES FROM backend_api.py HERE

@app.route('/')
def index():
    return render_template('incidents.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

Install dependencies:
```bash
pip install flask psycopg2-binary
```

### 3️⃣ Frontend (30 seconds)
```bash
# Create templates folder
mkdir templates

# Copy incidents page
cp incidents.html templates/
```

### 4️⃣ Run (10 seconds)
```bash
python app.py
```

Open browser: **http://localhost:5000**

## Test Drive

1. Click **"Report Issue"** button
2. Fill in:
   - Title: "Test Incident"
   - Description: "Testing the system"
   - Severity: Medium
3. Click **"Submit Issue"**
4. See your first incident! 🎉

## What's Next?

- Read `README.md` for full feature list
- Check `integration_guide.md` for production setup
- Customize colors/branding to match your app

## Troubleshooting

**Cannot connect to database:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check credentials in app.py get_connection()
```

**ModuleNotFoundError:**
```bash
pip install flask psycopg2-binary
```

**Port 5000 already in use:**
```python
# In app.py, change port
app.run(debug=True, port=8000)
```

---

That's it! You now have a full production incident tracking system running. 🚀
