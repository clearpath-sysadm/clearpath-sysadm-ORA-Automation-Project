# Admin Alert Bar Messaging System

## Implementation Report

**Task:** TASK-648 - Implement Admin Alert Bar Messaging System  
**Implementation Date:** January 7, 2026  
**Severity:** Enhancement  
**Status:** ✅ Completed

---

## Executive Summary

This task implements an admin-controlled messaging system that displays important alerts to all users at the top of every page. Administrators can create, activate, clear, and remove alerts through the Workflow Controls page. Active alerts (red bar) cannot be dismissed by users, while cleared alerts (green bar) can be dismissed and the dismissal persists in local storage.

**Key Outcomes:**
- Admins can communicate critical information to all users system-wide
- Active alerts ensure important messages are seen by everyone
- Cleared alerts allow users to acknowledge and dismiss notifications
- XSS protection prevents malicious script injection
- Proper role-based access control ensures only admins can modify alerts

---

## Problem Statement

### Business Need

There was no mechanism for administrators to communicate important information to all users of the Oracare Fulfillment System. When critical updates, system changes, or urgent notifications needed to be shared, there was no centralized way to ensure all logged-in users would see the message.

### Requirements

1. **Admin Message Creation:** Admins can create alert messages (max 255 characters)
2. **Alert Activation/Deactivation:** Admins can set alerts as "Active" (red) or "Cleared" (green)
3. **Alert Bar Display:** Alert displays at top of all pages for logged-in users
4. **User Dismissal:** Users can dismiss cleared (green) alerts; active (red) alerts cannot be dismissed
5. **Session Persistence:** Dismissed alerts stay dismissed until admin changes the alert
6. **Security:** HTML tags properly escaped to prevent XSS attacks

---

## Solution Implemented

### Architecture Overview

The system consists of four main components:

1. **Database Table:** `admin_alerts` stores the current alert message and status
2. **Flask API Endpoints:** GET (public) and POST (admin-only) for alert management
3. **JavaScript Alert Bar:** `alert-bar.js` displays alerts on all pages
4. **Admin UI:** Integrated into the Workflow Controls page

### Database Schema

```sql
CREATE TABLE admin_alerts (
    id SERIAL PRIMARY KEY,
    message VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);
```

**Design Decisions:**
- Single row design (id=1) simplifies management - only one global alert at a time
- `is_active` determines red (true) vs green (false) display
- Audit fields track who created/updated the alert and when

### API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/admin/alert` | GET | Public | Returns current alert (message, is_active, updated_at, updated_by) |
| `/api/admin/alert` | POST | Admin | Updates alert message and status |

**GET Response Example:**
```json
{
    "id": 1,
    "message": "System maintenance scheduled for tonight at 10 PM CST",
    "is_active": true,
    "updated_at": "2026-01-07T18:30:00",
    "updated_by": "admin@oracare.com"
}
```

**POST Request Example:**
```json
{
    "message": "New lot numbers have been assigned for Q1 2026",
    "is_active": true
}
```

### Security Implementation

A critical security consideration was ensuring the GET endpoint is public (for the alert bar to work) while the POST endpoint requires admin authentication.

**Solution:** Created a new route category `PUBLIC_GET_ADMIN_WRITE_ROUTES` in the authentication middleware:

```python
# Routes that are public for GET but require admin for write operations
PUBLIC_GET_ADMIN_WRITE_ROUTES = {
    '/api/admin/alert',  # Alert bar displays for all users (GET), but write requires admin
}

# Check if route is public for GET but requires admin for write operations
if request.path in PUBLIC_GET_ADMIN_WRITE_ROUTES:
    if request.method in {'GET', 'HEAD', 'OPTIONS'}:
        return None
    # For write operations, require admin
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'authenticated': False}), 401
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required', 'authenticated': True, 'role': current_user.role}), 403
    return None
```

**Security Tests:**
```bash
# GET without auth - should return alert data
curl http://localhost:5000/api/admin/alert
# Returns: {"id":1,"is_active":false,"message":"","updated_at":"...","updated_by":null}

# POST without auth - should return 401
curl -X POST -H "Content-Type: application/json" -d '{"message":"Test","is_active":true}' http://localhost:5000/api/admin/alert
# Returns: {"authenticated":false,"error":"Authentication required"}
```

### Frontend Implementation

**Alert Bar JavaScript (`static/js/alert-bar.js`):**

Key features:
- Fetches alert on page load
- Escapes HTML to prevent XSS attacks
- Uses localStorage to track dismissed alerts
- Adds body padding to prevent content overlap
- Red gradient for active alerts, green gradient for cleared alerts

```javascript
escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

**Dismissal Logic:**
- Stores a unique key combining message and status: `${message}_${isActive}`
- When admin changes alert (message or status), dismissed state resets
- Active alerts cannot be dismissed (no close button shown)

**Visual Design:**
- Fixed position at top of viewport
- z-index: 10000 to ensure visibility above all content
- Active: Red gradient (#dc3545 to #c82333) with white text
- Cleared: Green gradient (#28a745 to #218838) with white text
- Close button (X) only visible on cleared alerts

### Admin UI

The admin interface is integrated into the Workflow Controls page (`workflow_controls.html`):

**Features:**
- Textarea for message input with 255 character limit
- Live character counter
- Status indicator showing current alert state
- Three action buttons:
  - **Activate Alert** (red): Sets is_active=true
  - **Clear Alert** (green): Sets is_active=false
  - **Remove Alert** (gray): Clears message entirely
- Feedback messages for success/error states

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app.py` | Modified | Added API endpoints and authentication middleware |
| `static/js/alert-bar.js` | Created | Alert bar component for all pages |
| `static/js/auth.js` | Modified | Added getAuthStatus() method and window.auth alias |
| `workflow_controls.html` | Modified | Added admin UI for alert management |
| `index.html` | Modified | Added alert-bar.js script include |
| `order_audit.html` | Modified | Added alert-bar.js script include |
| `inventory_transactions.html` | Modified | Added alert-bar.js script include |
| `order-management.html` | Modified | Added alert-bar.js script include |
| `lot_inventory.html` | Modified | Added alert-bar.js script include |
| `weekly_shipped_history.html` | Modified | Added alert-bar.js script include |
| `sku_lot.html` | Modified | Added alert-bar.js script include |
| `charge_report.html` | Modified | Added alert-bar.js script include |
| `bundle_skus.html` | Modified | Added alert-bar.js script include |
| `email_contacts.html` | Modified | Added alert-bar.js script include |
| `shipped_items.html` | Modified | Added alert-bar.js script include |
| `help.html` | Modified | Added alert-bar.js script include |
| `shipped_orders.html` | Modified | Added alert-bar.js script include |
| `xml_import.html` | Modified | Added alert-bar.js script include |
| `incidents.html` | Modified | Added alert-bar.js script include |
| `settings.html` | Modified | Added alert-bar.js script include |
| `replit.md` | Modified | Added documentation for the new feature |

---

## Technical Details

### XSS Prevention

All alert messages are HTML-escaped before rendering to prevent cross-site scripting attacks:

```javascript
escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Usage
messageSpan.innerHTML = this.escapeHtml(this.alertData.message);
```

This approach:
- Creates a temporary DOM element
- Uses textContent (which doesn't parse HTML)
- Extracts the escaped HTML via innerHTML
- Safely handles <, >, &, quotes, etc.

### Local Storage Dismissal

Dismissed alerts are tracked using localStorage:

```javascript
// Key format combines message and status for uniqueness
const alertKey = `${this.alertData.message}_${isActive}`;

// Check if already dismissed
if (!isActive && this.dismissedVersion === alertKey) {
    return; // Don't show the bar
}

// On dismiss
localStorage.setItem('alertDismissed', alertKey);
```

**Behavior:**
- Changing the message creates a new key, resetting dismissal state
- Changing from cleared to active resets dismissal state
- Same message at same status respects previous dismissal

### Server Logging

Alert changes are logged for admin visibility on the Server Logs page:

```python
server_logger.info(f"Admin alert {status} by {current_user.email}: {message[:50]}{'...' if len(message) > 50 else ''}", source="Admin Alert")
```

---

## Testing & Verification

### Test Cases

| Scenario | Expected Result | Status |
|----------|-----------------|--------|
| Admin creates alert, activates it | Red bar displays on all pages | ✅ |
| Admin clears alert | Green bar displays, dismiss button visible | ✅ |
| User dismisses cleared alert | Bar hidden, stays hidden on refresh | ✅ |
| Admin activates after user dismissal | Red bar reappears for user | ✅ |
| Admin removes alert (empty message) | No bar displayed | ✅ |
| Non-admin attempts POST | 401/403 error returned | ✅ |
| XSS injection attempt | Script tags escaped, not executed | ✅ |
| Unauthenticated GET request | Alert data returned | ✅ |

### API Verification

```bash
# Verify GET is public
curl -s http://localhost:5000/api/admin/alert
# Output: {"id":1,"is_active":false,"message":"","updated_at":"2026-01-07T18:20:29.255299","updated_by":null}

# Verify POST requires auth
curl -s -X POST -H "Content-Type: application/json" -d '{"message":"Test","is_active":true}' http://localhost:5000/api/admin/alert
# Output: {"authenticated":false,"error":"Authentication required"}
```

---

## Usage Guide

### For Administrators

1. Navigate to **Workflow Controls** (Admin & Data section in sidebar)
2. Scroll down to the **Admin Alert Bar** section
3. Enter your message (max 255 characters)
4. Choose an action:
   - **Activate Alert**: Shows red bar that users cannot dismiss
   - **Clear Alert**: Shows green bar that users can dismiss
   - **Remove Alert**: Hides the alert bar entirely

### Alert Types

| Type | Color | Dismissible | Use Case |
|------|-------|-------------|----------|
| Active | Red | No | Critical announcements, system issues, urgent notices |
| Cleared | Green | Yes | Informational updates, resolved issues, acknowledgments |
| Removed | N/A | N/A | Return to normal operation |

---

## Production Deployment

### Deployment Steps

1. **Publish** the updated code to production via Replit's publish mechanism
2. **Apply Database Migration**: The `admin_alerts` table must be created in production:
   ```sql
   CREATE TABLE IF NOT EXISTS admin_alerts (
       id SERIAL PRIMARY KEY,
       message VARCHAR(255) NOT NULL,
       is_active BOOLEAN NOT NULL DEFAULT FALSE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       created_by VARCHAR(255),
       updated_by VARCHAR(255)
   );
   
   INSERT INTO admin_alerts (id, message, is_active, created_by)
   SELECT 1, '', FALSE, 'system'
   WHERE NOT EXISTS (SELECT 1 FROM admin_alerts WHERE id = 1);
   ```
3. **Verify** the Workflow Controls page loads the Admin Alert section
4. **Test** creating an alert and verify it appears on other pages

### Rollback Plan

If issues occur:
1. Previous checkpoints are available for rollback
2. The feature is isolated and does not affect core functionality
3. Removing the alert-bar.js script includes would disable the feature

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Database | Single-row `admin_alerts` table |
| API | GET (public) + POST (admin-only) at `/api/admin/alert` |
| Frontend | `alert-bar.js` included on all 17 HTML pages |
| Admin UI | Integrated into Workflow Controls page |
| Security | XSS escaping, proper auth middleware |
| Persistence | localStorage for dismissal state |
| Logging | Server logger events for admin visibility |

---

**Document Version:** 1.0  
**Author:** Oracare Development Team  
**Commits:** 
- `2147817a` - Add getAuthStatus method and window.auth alias
- `3f66b489` - Add admin alert API endpoints
- `a2e0afda` - Add alert-bar.js to all pages
- `beae92fb` - Add admin UI for alert management
- `c0a2b096` - Fix security: PUBLIC_GET_ADMIN_WRITE_ROUTES pattern
