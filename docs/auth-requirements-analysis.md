# Auth Requirements Analysis - ORA Business Automation

## Project Context

### 1. What is the project?
**ORA Business Automation Dashboard**
- **Purpose:** Internal business automation system for order processing, inventory management, and ShipStation integration
- **Tech stack:** Flask (Python backend), Vanilla JavaScript/HTML/CSS (frontend), SQLite database
- **Current stage:** Production - actively used for daily business operations
- **Number of users:** Single internal user (business operations team)

### 2. What framework/router?
- **Backend:** Flask 2.x (Python web framework)
- **Frontend:** Vanilla JavaScript with static HTML (no framework)
- **Routing:** Flask serves static HTML files via `send_from_directory()` + REST API endpoints
- **SSR:** None - static HTML files served directly (no templating)
- **Build tool:** None (static files served as-is)

---

## Current Auth Implementation

### 3. What auth system do you currently use?
**None - No user authentication currently implemented**
- This is an internal tool with no login system
- Access control relies on network/deployment restrictions (Replit private deployment)
- Duration: Since project inception
- Status: Acceptable for current single-user internal use case

### 4. What authentication methods?
**Currently: None**

**If auth were to be implemented, likely needs:**
- Email/password (primary method for internal users)
- No social login needed (internal tool)
- No magic links required
- No phone/SMS (unnecessary complexity)

### 5. Where does auth happen?
**Currently: N/A**

**If implemented, would need:**
- Server-side validation (Flask middleware)
- Client-side session checking
- API middleware for endpoint protection
- Token validation on both frontend and backend

---

## User Flows

### 6. Sign up flow
**Currently: N/A**

**If implemented:**
- Admin-only user creation (no self-service signup)
- Simple form: email, password, name, role
- No email verification needed (internal users verified out-of-band)
- No custom fields beyond basic profile
- No terms of service (internal tool)

### 7. Sign in flow
**Currently: N/A**

**If implemented:**
- Email/password form
- "Remember me" option preferred (7-30 day sessions)
- Redirect to dashboard after login
- No MFA/2FA needed initially (could add later for admins)

### 8. Password reset
**Currently: N/A**

**If implemented:**
- Email link to reset page (required feature)
- Self-service password reset important for small team
- Moderate usage expected (2-3 times per year)

### 9. Sign out
**Currently: N/A**

**If implemented:**
- Simple sign out button in header
- Redirect to login page after sign out
- Clear session token/cookie

---

## UI & UX

### 10. What UI library/components?
- **Current:** Custom CSS with CSS variables for theming
- **Design system:** Professional neutral palette, Inter font, 8px grid system
- **Components:** Vanilla JS components (cards, tables, modals)
- **Dark mode:** Toggle-based theme switching (localStorage persistence)
- **Auth UI needs:** Would build custom forms matching existing design system

### 11. What notification system?
**Current:** Basic browser alerts and inline error messages

**For auth, would need:**
- Toast notifications for success/error messages
- Could use simple custom toast system (matching existing design)
- No modal library currently (would build lightweight modal for auth dialogs)

### 12. Login page style
**If implemented:**
- Dedicated login page (full-page centered form)
- Match existing professional design (neutral colors, clean typography)
- No modal/dialog approach (cleaner UX for full auth flow)

### 13. Branding requirements
- Standard ORA branding across all pages
- Logo/colors already defined in CSS variables
- No white-label needs (single organization)
- Consistent design system already established

---

## Protected Routes

### 14. What needs protection?
**If auth implemented:**
- Entire dashboard application (all routes protected)
- No public pages needed
- All API endpoints require authentication
- 100% private application

### 15. Redirect behavior
**If implemented:**
- Redirect unauthenticated users to `/login`
- Remember intended destination (return after login)
- Single redirect pattern (all routes → login)

### 16. Loading states
**Current pattern:**
- Skeleton loaders for data fetching
- Would apply same pattern to auth check
- Show skeleton UI during auth verification
- Prevent flash of wrong content

---

## Authorization (Roles & Permissions)

### 17. Do you need roles?
**Currently: No**

**Future consideration:**
- Possible roles: Admin (full access), Viewer (read-only)
- Simple 2-role system sufficient
- Not critical for MVP auth implementation

### 18. Where are roles stored?
**If implemented:**
- SQLite database (new `users` table)
- Role stored as TEXT column ('admin', 'viewer')
- No JWT claims initially (session-based auth simpler)

### 19. What do roles control?
**If roles implemented:**
- UI element visibility (hide upload/edit buttons for viewers)
- API endpoint access (viewers can't POST/PUT/DELETE)
- No row-level security needed (all users see same data)

### 20. How are roles assigned?
**If implemented:**
- Admin assigns manually via settings page
- No auto-assignment
- No self-service role selection
- Simple admin panel for user management

---

## Backend Integration

### 21. What backend?
- **Framework:** Flask (Python)
- **Architecture:** Monolithic app (frontend + backend in same codebase)
- **API style:** REST endpoints (`/api/*` routes)
- **Same codebase:** Yes (Flask serves both HTML and API)

### 22. Token validation
**If implemented:**
- Server-side session cookies (Flask session management)
- Secure HttpOnly cookies preferred
- No token refresh needed (long-lived sessions with sliding expiration)
- Alternative: JWT tokens in HttpOnly cookies

### 23. Database
- **Current:** SQLite with WAL mode
- **User storage:** Would add `users` table to existing ora.db
- **Profile data:** Basic (id, email, password_hash, name, role, created_at)
- **Integration:** Use existing database utilities (`src/utils/db_utils.py`)

### 24. API protection
**If implemented:**
- All API endpoints require authentication
- No public endpoints
- No rate limiting needed (internal tool, trusted users)
- Same permission for all endpoints (or role-based for admin/viewer)

---

## Session Management

### 25. Session duration
**Preference:**
- Long sessions with sliding expiration (7-30 days)
- Extend session on activity
- No forced logout during active use
- Balance: security vs convenience for internal tool

### 26. Multi-device
**Requirements:**
- Allow multiple concurrent sessions (office computer + laptop)
- "Log out all sessions" feature useful
- No need to view active sessions list (overkill for small team)

### 27. Token storage
**Recommended approach:**
- Secure HttpOnly cookies (prevents XSS attacks)
- SameSite=Lax flag (CSRF protection)
- Secure flag in production (HTTPS only)
- No localStorage for tokens (security risk)

---

## Developer Experience

### 28. Testing
**Current state:** No automated tests

**Auth testing needs:**
- Mock auth for development
- Test account credentials in .env file
- Manual E2E testing sufficient initially
- Automated tests deferred to future enhancement

### 29. Local development
**Current setup:**
- Development uses same Replit environment
- No separate auth provider needed
- Uses SQLite database (same as production)
- Simple setup for new developers (clone and run)

### 30. Environment differences
**Current approach:**
- Single environment (Replit production)
- Development happens in Replit workspace
- No staging environment
- Auth config would be environment variable based

---

## Unique Requirements

### 31. Special features needed?
**Current needs: None**

**Future considerations:**
- Email verification: No (internal users)
- Account deletion: Yes (admin capability)
- Profile photo: No (unnecessary)
- Impersonation: No (no support use case)
- Account linking: No (single auth method)

### 32. Compliance/Security
**Requirements:**
- No GDPR (internal tool, no EU users)
- No HIPAA or healthcare regulations
- Audit logging: Nice-to-have (track who made changes)
- Password strength: Standard requirements (8+ chars, complexity)
- Security focus: Prevent unauthorized access, session hijacking

### 33. Integration with other services
**Current integrations:**
- ShipStation API (uses API keys, not user auth)
- Google Drive (uses service account, not user auth)
- SendGrid (optional, not currently used)
- No webhooks on auth events needed

---

## Migration & Adoption

### 34. Existing users
- **Current users:** 0 (no auth system exists)
- **Migration:** N/A (greenfield auth implementation)
- **Rollout:** Can deploy immediately (no gradual migration needed)

### 35. Timeline
- **Urgency:** Low (current access control via deployment restrictions is acceptable)
- **Priority:** Nice-to-have enhancement, not blocking
- **Rollout:** Single deployment (only one project)

### 36. Team
- **Developers:** 1 primary developer
- **Auth expertise:** Moderate (familiar with Flask-Login, session management)
- **Preference:** Simple over flexible (pragmatic implementation)
- **Maintenance:** Minimal ongoing maintenance preferred

---

## Pain Points

### 37. What's frustrating about current auth?
**Current state: No auth system**

**Potential concerns if auth not added:**
- No audit trail (can't track who made changes)
- No access control granularity (everyone has full access)
- Relies on deployment-level security (less granular)

### 38. What would make auth better?
**If implemented, priorities:**
- Minimal code (use Flask-Login or similar battle-tested library)
- Simple UI (clean login page matching existing design)
- Low maintenance (no complex token refresh, refresh flows)
- Clear session management (obvious when logged in/out)

### 39. What must not break?
**Critical requirements:**
- Existing API endpoints must continue working
- Dashboard functionality unchanged after auth added
- Database operations unaffected (add users table, don't modify existing)
- Dark mode, mobile responsiveness, existing UI features preserved

---

## Analysis Summary

### Current State
- **No authentication system** - Internal tool accessed via Replit deployment restrictions
- **Single user context** - Operations team uses shared access
- **API key auth only** - External services (ShipStation, Google) use API keys

### If Authentication Were to Be Implemented

#### Recommended Approach: Simple Flask Session-Based Auth

**Core Features (MVP):**
1. Email/password authentication
2. Server-side session cookies (HttpOnly, Secure, SameSite)
3. Password hashing with bcrypt
4. Simple login/logout pages
5. SQLite `users` table
6. Flask middleware for route protection

**Implementation Strategy:**
- Use **Flask-Login** library (battle-tested, minimal code)
- Session storage in Flask's secure cookies
- No role-based access control initially (add later if needed)
- Custom login UI matching existing design system
- **Important:** Since app serves static HTML (not templates), auth would require:
  - Converting protected routes to Flask views with `@login_required` decorator
  - Or adding client-side session checks with API validation
  - Or implementing reverse proxy auth at deployment level

**What to Build:**
- ✅ `users` table in SQLite (email, password_hash, name, created_at)
- ✅ Login/logout routes (`/login`, `/logout`)
- ✅ Password hashing (bcrypt)
- ✅ Session management (Flask-Login)
- ✅ API middleware to validate sessions (since static files served directly)
- ✅ Client-side auth check on page load (redirect to login if no valid session)
- ✅ Login page UI (matching current design)
- ✅ Session validation endpoint (`/api/auth/check`) for client-side verification

**What to Defer:**
- ❌ Roles/permissions (add only when multi-user scenario arises)
- ❌ Password reset (can be admin-initiated initially)
- ❌ Email verification (internal users don't need it)
- ❌ MFA/2FA (not required for internal tool)
- ❌ Social login (unnecessary complexity)

**Database Schema:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user', -- Future: 'admin', 'viewer'
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);
```

**Estimated Implementation:**
- 2-3 hours for basic Flask-Login integration
- 1-2 hours for UI (login page + logout button)
- 1 hour for testing and deployment
- **Total: 4-6 hours**

**Libraries Needed:**
```bash
pip install Flask-Login bcrypt
```

### Recommendation

**Current Priority: LOW**
- Existing deployment-level access control is adequate for current single-user scenario
- Implement authentication when:
  1. Multiple users need different access levels
  2. Audit trail becomes business requirement  
  3. Compliance or security policy mandates user-level auth

**If/When Implemented:**
- Keep it simple: Flask-Login + session cookies + basic login UI
- Don't over-engineer: No JWT, no OAuth, no microservices
- Match existing patterns: Use SQLite, follow current design system, maintain pragmatic approach
- Defer complexity: Start with basic auth, add roles/features only when needed

---

## Quick Reference

| Aspect | Current State | If Auth Implemented |
|--------|---------------|---------------------|
| **Auth System** | None | Flask-Login + sessions |
| **Storage** | N/A | SQLite users table |
| **Method** | N/A | Email/password |
| **Sessions** | N/A | HttpOnly cookies, 7-30 day |
| **Roles** | N/A | Defer to Phase 2 |
| **UI** | N/A | Custom login page |
| **Protection** | Deployment-level | Route decorators |
| **Complexity** | ⭐ None | ⭐⭐ Low (intentionally simple) |

---

**Document Created:** October 3, 2025  
**Status:** Analysis complete - Auth implementation deferred (not currently needed)  
**Next Steps:** Revisit when multi-user access or audit requirements emerge
