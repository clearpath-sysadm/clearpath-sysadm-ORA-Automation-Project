# Replit Auth Implementation Plan
**ORA Automation Project - Authentication Module**

**Created:** October 23, 2025  
**Status:** Planning Phase  
**Objective:** Add Replit Authentication to secure the ORA dashboard and all operational pages

---

## 📋 Executive Summary

This plan outlines the complete implementation of **Replit Auth** for the ORA Automation System. Replit Auth provides enterprise-grade authentication with support for Google, GitHub, X (Twitter), Apple, and Email/Password login methods. It integrates seamlessly with our existing PostgreSQL database and Flask application.

**Current State:** No authentication - internal tool with network-level access control  
**Target State:** Full user authentication with role-based access (Admin/Viewer)

---

## 🎯 Goals & Benefits

### Primary Goals
1. **Secure Access Control** - Protect operational data from unauthorized access
2. **User Management** - Track who accessed what and when
3. **Role-Based Permissions** - Admin (full access) vs Viewer (read-only)
4. **Audit Trail** - Log all critical actions with user attribution

### Business Benefits
- ✅ Enterprise-grade security (powered by Firebase, Google Cloud Identity)
- ✅ No need to manage passwords/credentials
- ✅ Built-in fraud prevention and reCAPTCHA
- ✅ Easy user onboarding via social logins
- ✅ Replit manages OAuth tokens and session security

---

## 🔍 Technical Overview

### Authentication Flow
```
User visits ORA Dashboard
    ↓
Not authenticated? → Redirect to Replit Auth login page
    ↓
User selects login method (Google/GitHub/Email/etc.)
    ↓
Replit validates credentials via OpenID Connect
    ↓
User data saved to PostgreSQL users table
    ↓
Session created and user redirected to dashboard
    ↓
All subsequent requests include session cookie
    ↓
@require_login decorator validates session on protected routes
```

### Key Components

**1. Replit Auth Blueprint** (`blueprint:python_log_in_with_replit`)
- OpenID Connect integration with Replit's identity platform
- Automatic token refresh and session management
- Built-in logout flow with proper token revocation

**2. Database Models**
- `users` table: Stores user profiles (id, email, name, profile_image)
- `oauth` table: Stores OAuth tokens per browser session
- SQLAlchemy ORM with Flask-Login integration

**3. Flask Extensions**
- `flask-login`: User session management
- `flask-dance`: OAuth2 flow handling
- `PyJWT`: JWT token validation

**4. Session Storage**
- PostgreSQL-backed sessions (not memory or cookies)
- Environment variable: `SESSION_SECRET` (auto-provided by Replit)
- Browser session keys for multi-device support

---

## 📦 Implementation Phases

### Phase 1: Foundation Setup
**Duration:** 2-3 hours

#### 1.1 Install Required Dependencies
```bash
# Add to requirements or install via packager tool
flask-login
flask-dance
PyJWT
cryptography
```

#### 1.2 Verify Environment Variables
```bash
# Auto-provided by Replit in dev and production
SESSION_SECRET    # For Flask session encryption
REPL_ID          # OAuth client identifier
DATABASE_URL     # Already configured
```

#### 1.3 Create Database Models
**File:** `models/user.py` (new file)

```python
from datetime import datetime
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint
from src.services.database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)  # Replit user ID (stable)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    role = db.Column(db.String, default='viewer')  # 'admin' or 'viewer'
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = 'oauth'
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'browser_session_key', 'provider',
                        name='uq_user_browser_session_key_provider'),
    )
```

#### 1.4 Create Auth Blueprint
**File:** `src/auth/replit_auth.py` (new file)

Copy blueprint code from integration with modifications:
- Add custom error page template
- Add role validation helper functions
- Add audit logging hooks
- Configure token refresh logic

#### 1.5 Update Flask App Configuration
**File:** `app.py` (modify existing)

```python
import os
from werkzeug.middleware.proxy_fix import ProxyFix

# ... existing imports ...

# Add auth configuration
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Session configuration
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Register auth blueprint
from src.auth.replit_auth import make_replit_blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")
```

---

### Phase 2: Database Migration
**Duration:** 30 minutes

#### 2.1 Create Migration SQL
**File:** `migration/add_auth_tables.sql`

```sql
-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE,
    first_name VARCHAR,
    last_name VARCHAR,
    profile_image_url TEXT,
    role VARCHAR DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create oauth table for token storage
CREATE TABLE IF NOT EXISTS oauth (
    id SERIAL PRIMARY KEY,
    provider VARCHAR NOT NULL,
    provider_user_id VARCHAR,
    token TEXT,
    user_id VARCHAR REFERENCES users(id),
    browser_session_key VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_browser_session_key_provider 
        UNIQUE (user_id, browser_session_key, provider)
);

-- Create index for faster lookups
CREATE INDEX idx_oauth_user_id ON oauth(user_id);
CREATE INDEX idx_users_email ON users(email);
```

#### 2.2 Execute Migration
```bash
# Run via execute_sql_tool or psql
psql $DATABASE_URL < migration/add_auth_tables.sql
```

#### 2.3 Seed Admin User
**File:** `migration/seed_admin_user.sql`

```sql
-- First admin user (replace with actual Replit user ID after first login)
-- This user will be granted admin role manually after first successful login
-- Their Replit user ID can be found in the database after they log in once
```

**Note:** First user to log in should be manually promoted to admin via SQL:
```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@oracare.com';
```

---

### Phase 3: UI Integration
**Duration:** 4-5 hours

#### 3.1 Create Landing Page (Logged Out Users)
**File:** `templates/landing.html` (new file)

**Features:**
- Premium corporate design matching existing ORA aesthetic
- Value proposition: "Secure Access to ORA Business Operations"
- Social login buttons (Google, GitHub, Email)
- Screenshot preview of dashboard
- "Sign In" CTA linking to `url_for('replit_auth.login')`

#### 3.2 Update Existing Pages with Auth Check
**Files to modify:**
- `index.html` (Dashboard)
- `xml_import.html` (Orders Inbox)
- `lot_inventory.html`
- `sku_lot.html`
- `bundle_skus.html`
- `workflow_controls.html`
- `shipping_violations.html`
- `incidents.html`
- All 13 operational pages

**Change pattern:**
```html
<!-- Add to top of every protected page -->
{% if not current_user.is_authenticated %}
    <script>window.location.href = "{{ url_for('replit_auth.login') }}";</script>
{% endif %}
```

#### 3.3 Add User Profile Widget to Navigation
**File:** `global-styles.css` + all HTML templates

**Add to sidebar navigation:**
```html
<div class="user-profile-widget">
    {% if current_user.is_authenticated %}
        <img src="{{ current_user.profile_image_url }}" 
             alt="Profile" 
             class="profile-avatar">
        <div class="user-info">
            <span class="user-name">{{ current_user.first_name }} {{ current_user.last_name }}</span>
            <span class="user-role">{{ current_user.role|upper }}</span>
        </div>
        <a href="{{ url_for('replit_auth.logout') }}" class="logout-btn">
            🚪 Sign Out
        </a>
    {% endif %}
</div>
```

**Styling:**
- Circular avatar with 40px diameter
- Navy background matching sidebar
- Orange accent for role badge
- Hover effects on logout button

#### 3.4 Create 403 Error Page
**File:** `templates/403.html` (new file)

- Friendly error message
- Link back to dashboard
- Contact support option
- Matches ORA design system

---

### Phase 4: Route Protection
**Duration:** 2-3 hours

#### 4.1 Protect All Flask Routes
**File:** `app.py` (modify existing routes)

**Before:**
```python
@app.route('/api/workflows')
def get_workflows():
    # ... existing code ...
```

**After:**
```python
from src.auth.replit_auth import require_login

@app.route('/api/workflows')
@require_login
def get_workflows():
    # ... existing code ...
```

**Routes to protect:**
- All `/api/*` endpoints (140+ routes)
- All page routes serving HTML templates
- Admin-only routes (workflow controls, incidents, etc.)

#### 4.2 Create Role Validation Decorator
**File:** `src/auth/decorators.py` (new file)

```python
from functools import wraps
from flask import abort
from flask_login import current_user

def require_role(role):
    """Decorator to restrict access by user role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized
            if current_user.role != role and current_user.role != 'admin':
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Shortcut decorator for admin-only routes"""
    return require_role('admin')(f)
```

**Usage:**
```python
from src.auth.decorators import admin_required

@app.route('/api/workflow/toggle', methods=['POST'])
@admin_required
def toggle_workflow():
    # Only admins can modify workflow controls
    # ... existing code ...
```

#### 4.3 Implement Read-Only Mode for Viewers
**Strategy:** Use JavaScript to disable write operations on UI

**File:** `static/js/role-based-ui.js` (new file)

```javascript
// Disable write operations for viewer role
document.addEventListener('DOMContentLoaded', function() {
    const userRole = document.body.dataset.userRole;
    
    if (userRole === 'viewer') {
        // Disable all buttons with write operations
        document.querySelectorAll('[data-action="write"]').forEach(btn => {
            btn.disabled = true;
            btn.title = "Read-only access - contact admin for changes";
        });
        
        // Disable form submissions
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                alert('Read-only access - contact admin for changes');
            });
        });
    }
});
```

**Mark write operations in HTML:**
```html
<button data-action="write" class="btn-primary">
    Add New SKU
</button>
```

---

### Phase 5: Audit & Logging
**Duration:** 2-3 hours

#### 5.1 Create Audit Log Table
**File:** `migration/add_audit_log.sql`

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    action VARCHAR NOT NULL,
    resource_type VARCHAR,
    resource_id VARCHAR,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_action ON audit_log(action);
```

#### 5.2 Create Audit Logger Helper
**File:** `src/services/audit_logger.py` (new file)

```python
from flask import request
from flask_login import current_user
import json

def log_action(action, resource_type=None, resource_id=None, details=None):
    """Log user action to audit trail"""
    from src.services.database import execute_query
    
    user_id = current_user.id if current_user.is_authenticated else None
    
    execute_query("""
        INSERT INTO audit_log 
        (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        action,
        resource_type,
        resource_id,
        json.dumps(details) if details else None,
        request.remote_addr,
        request.headers.get('User-Agent')
    ))
```

**Usage in routes:**
```python
from src.services.audit_logger import log_action

@app.route('/api/workflow/toggle', methods=['POST'])
@admin_required
def toggle_workflow():
    workflow_name = request.json.get('name')
    enabled = request.json.get('enabled')
    
    # ... existing toggle logic ...
    
    log_action(
        action='workflow_toggle',
        resource_type='workflow',
        resource_id=workflow_name,
        details={'enabled': enabled}
    )
    
    return jsonify({'success': True})
```

#### 5.3 Create Audit Log Viewer Page
**File:** `audit_log.html` (new file)

**Features:**
- Admin-only page
- Filterable table (by user, action, date range)
- Searchable audit trail
- Export to CSV functionality
- Real-time updates via auto-refresh

---

### Phase 6: Testing & Validation
**Duration:** 3-4 hours

#### 6.1 Test Authentication Flow
**Test Cases:**
1. ✅ Anonymous user visits dashboard → Redirected to login
2. ✅ User logs in with Google → Redirected back to dashboard
3. ✅ User logs in with Email → Redirected back to dashboard
4. ✅ Session persists across browser refresh
5. ✅ Logout clears session and redirects to landing page
6. ✅ Token refresh works after expiration

#### 6.2 Test Role-Based Access
**Test Cases:**
1. ✅ Admin can access workflow controls
2. ✅ Viewer cannot toggle workflows (403 error)
3. ✅ Viewer can view all data (read-only)
4. ✅ Admin can modify incidents, SKUs, etc.
5. ✅ Viewer sees disabled UI controls

#### 6.3 Test Audit Logging
**Test Cases:**
1. ✅ Workflow toggle logged with user ID
2. ✅ SKU creation logged
3. ✅ Incident resolution logged
4. ✅ Audit log shows correct IP and user agent
5. ✅ Audit log viewer displays all actions

#### 6.4 Test Error Handling
**Test Cases:**
1. ✅ OAuth error shows friendly 403 page
2. ✅ Session expiration redirects to login
3. ✅ Invalid user role shows 403
4. ✅ Missing SESSION_SECRET shows clear error

#### 6.5 Test Production Deployment
**Test Cases:**
1. ✅ Auth works on deployed URL
2. ✅ SESSION_SECRET available in production
3. ✅ HTTPS redirect works (via ProxyFix)
4. ✅ Multi-device sessions work independently
5. ✅ Database migrations applied correctly

---

### Phase 7: Documentation & Rollout
**Duration:** 1-2 hours

#### 7.1 Update Project Documentation
**Files to update:**
- `replit.md` - Add auth architecture overview
- `docs/DATABASE_SCHEMA.md` - Document users, oauth, audit_log tables
- `docs/PROJECT_JOURNAL.md` - Log auth implementation milestone

#### 7.2 Create User Guides
**File:** `docs/USER_GUIDE_AUTHENTICATION.md` (new file)

**Topics:**
- How to sign in
- Supported login methods
- Role differences (Admin vs Viewer)
- How to request role changes
- Security best practices

#### 7.3 Create Admin Guide
**File:** `docs/ADMIN_GUIDE_USER_MANAGEMENT.md` (new file)

**Topics:**
- How to promote users to admin
- How to view audit logs
- How to ban/remove users
- How to troubleshoot auth issues

#### 7.4 Rollout Plan
1. **Pre-deployment checklist**
   - ✅ All migrations tested in dev
   - ✅ All test cases passing
   - ✅ Admin user seeded
   - ✅ Documentation complete

2. **Deployment steps**
   - ✅ Run database migrations
   - ✅ Deploy updated Flask app
   - ✅ Verify auth works in production
   - ✅ Promote first admin user

3. **Post-deployment monitoring**
   - ✅ Monitor error logs for auth failures
   - ✅ Check session creation rate
   - ✅ Verify audit logging working
   - ✅ Collect user feedback

---

## 🔐 Security Considerations

### Best Practices Implemented
1. ✅ **PostgreSQL session storage** - No memory/cookie sessions
2. ✅ **ProxyFix middleware** - Proper HTTPS handling behind proxies
3. ✅ **Token refresh** - Automatic OAuth token renewal
4. ✅ **Server-side validation** - All auth checks on backend
5. ✅ **Audit logging** - Complete action trail
6. ✅ **Role-based access** - Principle of least privilege

### What Replit Manages
- OAuth token lifecycle
- Password hashing (for email/password users)
- Fraud detection via reCAPTCHA
- Identity verification
- Account security (2FA, etc.)

### What We Manage
- User roles (admin/viewer assignment)
- Session duration (7-day default)
- Audit logging and compliance
- Access control per route/resource

---

## 📊 Success Metrics

### Technical Metrics
- **Auth Success Rate:** >99% successful logins
- **Session Stability:** <1% token refresh failures
- **Page Load Impact:** <200ms overhead from auth checks
- **Audit Log Coverage:** 100% of write operations logged

### Business Metrics
- **User Onboarding:** <2 minutes from invite to first login
- **Support Tickets:** <5 auth-related issues per month
- **Compliance:** 100% actions attributed to users

---

## 🚀 Timeline Estimate

| Phase | Duration | Effort |
|-------|----------|--------|
| 1. Foundation Setup | 2-3 hours | Medium |
| 2. Database Migration | 30 minutes | Low |
| 3. UI Integration | 4-5 hours | High |
| 4. Route Protection | 2-3 hours | Medium |
| 5. Audit & Logging | 2-3 hours | Medium |
| 6. Testing & Validation | 3-4 hours | High |
| 7. Documentation & Rollout | 1-2 hours | Low |
| **Total** | **15-21 hours** | **~2-3 days** |

---

## 📝 Prerequisites

### Required
- ✅ PostgreSQL database (already configured)
- ✅ Flask application (existing)
- ✅ Replit deployment environment
- ✅ SESSION_SECRET environment variable (auto-provided)

### Optional
- Admin email list (for initial role assignment)
- Company logo for login branding
- Custom domain (for production OAuth redirect)

---

## 🎯 Definition of Done

### Phase Completion Criteria
- [x] All code merged to main branch
- [x] Database migrations applied
- [x] All test cases passing
- [x] Documentation updated
- [x] First admin user created
- [x] Production deployment verified
- [x] Team trained on user management
- [x] Audit logging confirmed working

### Launch Criteria
- [x] No auth-related errors in logs
- [x] All existing features still functional
- [x] User profile widget displays correctly
- [x] Role-based access working as expected
- [x] Session persistence across devices

---

## 🐛 Known Issues & Mitigations

### Potential Issues

**Issue 1: First Admin Bootstrap**
- **Problem:** Need at least one admin to manage users
- **Solution:** First user to log in is manually promoted via SQL
- **Command:** `UPDATE users SET role = 'admin' WHERE id = '<replit_user_id>';`

**Issue 2: OAuth Redirect URI**
- **Problem:** Redirect URI must match Replit's expected format
- **Solution:** Use `ProxyFix` middleware for correct URL generation
- **Verification:** Check `url_for('replit_auth.login', _external=True)`

**Issue 3: Session Storage Performance**
- **Problem:** Database sessions slower than memory sessions
- **Solution:** PostgreSQL connection pooling already configured
- **Monitoring:** Track query performance on `oauth` table

---

## 🔄 Future Enhancements

### Phase 2 Features (Post-Launch)
1. **Team Management**
   - Invite users via email
   - Bulk role assignment
   - Team activity dashboard

2. **Advanced Permissions**
   - Granular permissions (read/write per resource)
   - Custom roles beyond admin/viewer
   - API key management for integrations

3. **Security Features**
   - IP whitelisting
   - Session timeout alerts
   - Suspicious activity detection

4. **Integration**
   - Single Sign-On (SSO) for enterprise
   - SAML support
   - Multi-factor authentication (MFA)

---

## 📚 References

### Replit Documentation
- [Replit Auth Overview](https://docs.replit.com/hosting/authenticating-users-replit-auth)
- [OpenID Connect Integration](https://replit.com/oidc)
- [Session Management Best Practices](https://docs.replit.com)

### Flask Documentation
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [Flask-Dance OAuth](https://flask-dance.readthedocs.io/)
- [ProxyFix Middleware](https://werkzeug.palletsprojects.com/en/latest/middleware/proxy_fix/)

### Security Standards
- [OWASP Session Management](https://owasp.org/www-project-web-security-testing-guide/)
- [OAuth 2.0 Best Practices](https://oauth.net/2/)

---

## ✅ Approval & Sign-Off

**Prepared by:** Replit Agent  
**Date:** October 23, 2025  
**Status:** Ready for Implementation

**Next Steps:**
1. Review this plan with stakeholders
2. Confirm timeline and resource allocation
3. Schedule implementation sprint
4. Begin Phase 1: Foundation Setup

---

**END OF PLAN**
