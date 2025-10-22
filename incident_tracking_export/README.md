# 🚨 Incident Tracking System

A complete production incident management system with notes, screenshots, filtering, and emoji support.

## ✨ Features

- ✅ **Full CRUD operations** (Create, Read, Update, Delete)
- ✅ **Status workflow** (New → In Progress → Resolved → Closed)
- ✅ **Severity levels** (Low, Medium, High, Critical)
- ✅ **Notes/Updates system** with timestamps
- ✅ **Screenshot attachments** (drag & drop, clipboard paste, up to 16MB)
- ✅ **Filtering** by status and severity
- ✅ **Responsive design** (desktop table + mobile cards)
- ✅ **Emoji support** in all text fields
- ✅ **Change detection** (warns before losing unsaved edits)
- ✅ **Global "Report Issue" button** accessible from any page
- ✅ **Cause & Resolution fields** for post-mortem documentation

## 📁 Files Included

```
incident_tracking_export/
├── README.md                    # This file
├── database_schema.sql          # PostgreSQL database schema
├── backend_api.py               # Flask API endpoints (Python)
├── incidents.html               # Complete frontend UI
└── integration_guide.md         # Step-by-step integration instructions
```

## 🚀 Quick Start

### 1. Database Setup

```bash
# Run the schema against your PostgreSQL database
psql -U your_user -d your_database -f database_schema.sql
```

### 2. Backend Integration (Flask)

Add the routes from `backend_api.py` to your Flask application:

```python
# In your app.py
from flask import Flask, request, jsonify, Response
import mimetypes
import psycopg2
import os

app = Flask(__name__)

# Your database connection function
def get_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

# Copy all routes from backend_api.py here
# (or import them from a separate module)
```

### 3. Frontend Setup

Copy `incidents.html` to your templates or static folder:

```bash
# For Flask with templates
cp incidents.html /path/to/your/templates/

# Or serve as static HTML
cp incidents.html /path/to/your/static/
```

### 4. Add Global Report Button (Optional)

Add this button to your navigation on any page:

```html
<button class="btn btn-critical" onclick="window.location.hash='report'">
    🚨 Report Issue
</button>
```

## 🎨 Styling Requirements

The incidents.html file includes embedded styles, but it also uses CSS custom properties (variables) for theming. Ensure your global stylesheet defines these variables:

```css
:root {
    --primary-navy: #1B2A4A;
    --accent-orange: #F2994A;
    --bg-primary: #FFFFFF;
    --bg-secondary: #F8F9FA;
    --text-primary: #2C3E50;
    --text-secondary: #6C757D;
    --border-color: #DEE2E6;
    --critical-red: #DC3545;
    --success-green: #28A745;
    --warning-yellow: #FFC107;
    --info-blue: #17A2B8;
    --spacing-unit: 8px;
    --border-radius: 8px;
    --border-radius-sm: 4px;
    --border-radius-md: 6px;
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* Dark mode support */
[data-theme="dark"] {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --border-color: #404040;
}
```

## 🔧 API Endpoints

### Incidents
- `GET /api/incidents` - Get all incidents (with optional filters)
- `POST /api/incidents` - Create new incident
- `PUT /api/incidents/<id>` - Update incident (status or full edit)

### Notes
- `POST /api/incidents/<id>/notes` - Add note to incident

### Screenshots
- `GET /api/incidents/<id>/screenshots` - Get screenshot list
- `POST /api/incidents/<id>/screenshots` - Upload screenshot
- `GET /api/screenshots/<id>` - Get screenshot binary data
- `DELETE /api/screenshots/<id>` - Delete screenshot

## 📊 Database Schema

### Tables
- `production_incidents` - Main incidents table
- `incident_notes` - Timeline notes/updates
- `production_incident_screenshots` - Screenshot storage (BYTEA)

### Key Fields
- **Severity**: low, medium, high, critical
- **Status**: new, in_progress, resolved, closed
- **Cause**: Root cause analysis (optional, supports emoji)
- **Resolution**: How it was resolved (optional, supports emoji)

## 🎯 Usage Examples

### Create an Incident (JavaScript)
```javascript
const response = await fetch('/api/incidents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        title: 'Database Connection Error',
        description: 'Users unable to login - connection timeout',
        severity: 'critical',
        reported_by: 'John Doe'
    })
});
const data = await response.json();
console.log('Incident ID:', data.incident_id);
```

### Update Status
```javascript
await fetch('/api/incidents/123', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'in_progress' })
});
```

### Add Note
```javascript
await fetch('/api/incidents/123/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        note: 'Identified issue in database pool configuration',
        note_type: 'user',
        created_by: 'Tech Team'
    })
});
```

## 🌐 Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## 📝 License

This code is provided as-is for integration into your projects. No attribution required.

## 🤝 Support

For issues or questions, refer to the integration guide or contact your development team.

## 🎨 Customization

### Change Color Scheme
Edit the CSS custom properties in `incidents.html` or your global stylesheet.

### Modify Severity Levels
Update the `severity` CHECK constraint in `database_schema.sql` and the dropdown options in `incidents.html`.

### Add Custom Fields
1. Add column to `production_incidents` table
2. Update API routes to handle new field
3. Add form field to `incidents.html`

## 📸 Screenshots

The system includes:
- **Report Modal**: Quick issue reporting with screenshot paste
- **Detail View**: Full incident details with timeline
- **Edit Modal**: Complete incident editing with cause/resolution
- **Table View**: Sortable, filterable incident list
- **Mobile View**: Responsive card layout for small screens

## 🔒 Security Considerations

- Validate all user input on the backend
- Implement authentication/authorization for API endpoints
- Consider file type validation for screenshots beyond MIME type
- Add rate limiting for screenshot uploads
- Sanitize HTML output to prevent XSS (already implemented with `escapeHtml()`)

## 🚀 Production Deployment

1. Set up proper database backups
2. Configure environment variables for database connection
3. Enable HTTPS for secure screenshot uploads
4. Set up monitoring for disk space (screenshots stored in DB)
5. Consider archiving old incidents to separate table/database

---

**Total Code**: ~2,500 lines (HTML/CSS/JS/Python combined)  
**Database Storage**: Screenshots stored as BYTEA (consider file system for production at scale)  
**Performance**: Indexed for fast filtering and searching
