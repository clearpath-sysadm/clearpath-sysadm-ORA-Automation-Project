# 📘 Integration Guide - Incident Tracking System

Step-by-step instructions for integrating the incident tracking system into your existing project.

## Prerequisites

- PostgreSQL database (9.5+)
- Flask web framework (Python 3.7+)
- psycopg2 library for database connectivity
- Basic HTML/CSS/JavaScript knowledge

## Step 1: Database Setup

### Option A: Run SQL File
```bash
psql -U your_username -d your_database -f database_schema.sql
```

### Option B: Manual Execution
1. Open your PostgreSQL client
2. Copy contents of `database_schema.sql`
3. Execute against your database

### Verify Installation
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE '%incident%';

-- Should return:
-- production_incidents
-- incident_notes
-- production_incident_screenshots
```

## Step 2: Backend Integration (Flask)

### 2.1 Install Dependencies
```bash
pip install flask psycopg2-binary
```

### 2.2 Add Database Connection Function

In your `app.py`, ensure you have a database connection function:

```python
import psycopg2
import os

def get_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        os.getenv('DATABASE_URL')
        # Or specify manually:
        # host="localhost",
        # database="your_db",
        # user="your_user",
        # password="your_password"
    )
```

### 2.3 Add API Routes

Copy all routes from `backend_api.py` into your `app.py`:

```python
# At the top of app.py
from flask import Flask, request, jsonify, Response
import mimetypes

app = Flask(__name__)

# Your existing routes...

# ADD ALL ROUTES FROM backend_api.py HERE
# Starting with @app.route('/api/incidents', methods=['GET'])
# ...
```

### 2.4 Test Backend

```bash
# Start your Flask app
python app.py

# Test in another terminal
curl http://localhost:5000/api/incidents

# Should return: {"success": true, "incidents": []}
```

## Step 3: Frontend Setup

### 3.1 Copy HTML File

```bash
# For Flask with templates
cp incidents.html /path/to/your/app/templates/

# For static serving
cp incidents.html /path/to/your/app/static/
```

### 3.2 Update Navigation

Add link to incidents page in your main navigation:

```html
<!-- In your navbar/sidebar -->
<nav>
    <a href="/incidents.html">🚨 Incidents</a>
    <!-- or if using Flask templates: -->
    <a href="{{ url_for('serve_incidents') }}">🚨 Incidents</a>
</nav>
```

### 3.3 Add Flask Route (if using templates)

```python
@app.route('/incidents')
def serve_incidents():
    return render_template('incidents.html')
```

## Step 4: Global Report Button (Optional)

Add a "Report Issue" button to any page that opens the incident modal:

### 4.1 Add Button to HTML
```html
<!-- In your page header/navbar -->
<button class="btn btn-critical" onclick="window.location.href='/incidents.html#report'">
    🚨 Report Issue
</button>
```

### 4.2 Auto-Open Modal Script
The incidents.html already includes this, but for reference:

```javascript
// Auto-open report modal if URL has #report hash
window.addEventListener('DOMContentLoaded', () => {
    if (window.location.hash === '#report') {
        document.getElementById('report-modal').style.display = 'flex';
    }
});
```

## Step 5: Styling Integration

### 5.1 Use Embedded Styles (Easiest)
The `incidents.html` file includes all necessary styles. No additional CSS required!

### 5.2 Use Global Stylesheet (Advanced)

If you want to extract styles to a global stylesheet:

1. Copy the `<style>` block from incidents.html
2. Save to `static/css/incidents.css`
3. Replace style block with:
```html
<link rel="stylesheet" href="/static/css/incidents.css">
```

### 5.3 Customize Theme

Edit CSS custom properties to match your brand:

```css
:root {
    --primary-navy: #1B2A4A;      /* Your primary color */
    --accent-orange: #F2994A;     /* Your accent color */
    --critical-red: #DC3545;      /* Error/critical color */
    --success-green: #28A745;     /* Success color */
}
```

## Step 6: Testing

### 6.1 Test Create Incident
1. Navigate to `/incidents.html`
2. Click "Report Issue" button
3. Fill in title, description, severity
4. Click "Submit Issue"
5. Verify incident appears in table

### 6.2 Test Screenshot Upload
1. Open an incident (click "View")
2. Drag & drop an image, or paste from clipboard
3. Verify image appears in gallery

### 6.3 Test Filtering
1. Create incidents with different statuses/severities
2. Use dropdown filters
3. Verify table updates correctly

### 6.4 Test Status Change
1. Open incident detail view
2. Change status dropdown
3. Confirm the change
4. Verify status badge updates

## Step 7: Production Considerations

### 7.1 Database Backups
```bash
# Set up automated PostgreSQL backups
pg_dump -U username dbname > backup_$(date +%Y%m%d).sql
```

### 7.2 File Size Monitoring
Screenshots are stored in database (BYTEA). Monitor disk usage:

```sql
-- Check total screenshot storage
SELECT 
    COUNT(*) as screenshot_count,
    pg_size_pretty(SUM(LENGTH(file_data))) as total_size
FROM production_incident_screenshots;
```

### 7.3 Add Authentication

Protect endpoints with authentication:

```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Your auth logic here
        if not session.get('user_id'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/incidents', methods=['POST'])
@require_auth
def create_incident():
    # ... existing code
```

### 7.4 Performance Optimization

For large datasets, add pagination:

```python
@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    offset = (page - 1) * per_page
    
    # Add LIMIT and OFFSET to query
    query += f" LIMIT {per_page} OFFSET {offset}"
    # ... rest of code
```

## Step 8: Customization Examples

### 8.1 Add Custom Severity Level

**Database:**
```sql
ALTER TABLE production_incidents 
DROP CONSTRAINT production_incidents_severity_check;

ALTER TABLE production_incidents 
ADD CONSTRAINT production_incidents_severity_check 
CHECK (severity IN ('low', 'medium', 'high', 'critical', 'urgent'));
```

**Frontend (incidents.html):**
```html
<!-- Add to severity dropdown -->
<option value="urgent">Urgent - Immediate attention required</option>
```

**CSS:**
```css
.severity-badge.severity-urgent {
    background: #FF0000;
    color: white;
}
```

### 8.2 Add Email Notifications

```python
from flask_mail import Mail, Message

@app.route('/api/incidents', methods=['POST'])
def create_incident():
    # ... create incident code ...
    
    # Send email notification
    msg = Message(
        subject=f'New Incident: {title}',
        recipients=['team@example.com'],
        body=f'Severity: {severity}\n\n{description}'
    )
    mail.send(msg)
    
    return jsonify({'success': True, 'incident_id': incident_id})
```

### 8.3 Add Assignee Field

**Database:**
```sql
ALTER TABLE production_incidents 
ADD COLUMN assigned_to VARCHAR(255);
```

**Backend:**
```python
# Update GET query
query = """
    SELECT id, title, description, severity, status, reported_by, 
           created_at, updated_at, cause, resolution, assigned_to
    FROM production_incidents
    WHERE 1=1
"""

# Update result building
result.append({
    # ... existing fields ...
    'assigned_to': inc[10],
})
```

**Frontend:**
```html
<!-- Add to edit form -->
<div class="form-group">
    <label for="edit-incident-assigned">Assigned To</label>
    <input type="text" id="edit-incident-assigned" placeholder="Enter name">
</div>
```

## Troubleshooting

### Issue: "Cannot connect to database"
**Solution:** Verify DATABASE_URL environment variable is set correctly

### Issue: "Screenshot upload fails"
**Solution:** Check file size (max 16MB) and PostgreSQL max_allowed_packet setting

### Issue: "Emojis display as question marks"
**Solution:** Ensure database encoding is UTF-8:
```sql
SHOW SERVER_ENCODING;  -- Should show UTF8
```

### Issue: "Modal doesn't open"
**Solution:** Check browser console for JavaScript errors, verify all script tags are present

## Next Steps

1. ✅ Set up automated database backups
2. ✅ Add user authentication
3. ✅ Configure email notifications
4. ✅ Add incident export (CSV/PDF)
5. ✅ Set up monitoring/alerting for critical incidents
6. ✅ Create incident analytics dashboard

## Support Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Flask Documentation: https://flask.palletsprojects.com/
- JavaScript Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API

---

**Integration Time Estimate:** 30-60 minutes  
**Difficulty:** Intermediate  
**Maintenance:** Low (self-contained system)
