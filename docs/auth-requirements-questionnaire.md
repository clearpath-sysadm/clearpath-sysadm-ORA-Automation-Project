# Auth Requirements Discovery Questionnaire

## Purpose

Before building a reusable authentication package, it's critical to understand the real requirements across all projects that will use it. This questionnaire helps you:

- **Avoid over-engineering** - Build only what you actually need, not what sounds theoretically good
- **Identify common patterns** - Find what's truly shared vs what just seems similar
- **Design the right abstractions** - Know where to be flexible and where to be opinionated
- **Prevent costly rewrites** - Catch incompatibilities before building the package
- **Set realistic scope** - Understand the true complexity of what you're building

By systematically comparing your projects, you'll discover:
- What must be in the core package (identical across all projects)
- What should be configurable (varies but predictably)
- What should stay project-specific (too different to share)

This analysis typically reveals that less than 50% of auth code can be truly shared. That's okay - it's better to share the right 50% than force-fit everything into a brittle abstraction.

**Time investment:** 1-2 hours to complete this questionnaire will save weeks of building the wrong thing.

---

## Instructions

1. Answer each question for all your projects
2. Create a comparison table to identify patterns
3. Look for commonalities (what to share) and differences (what to make configurable)

---

## Project Context

### 1. What is the project?
- Project name/purpose
- Tech stack (React, Next.js, Vue, etc.)
- Current stage (production, development, prototype)
- Number of users (or expected users)

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 2. What framework/router?
- Frontend framework and version
- Routing library (React Router, Next.js router, Wouter, etc.)
- SSR or client-side only?
- Build tool (Vite, Next.js, CRA, etc.)

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Current Auth Implementation

### 3. What auth system do you currently use?
- Firebase? Custom? Auth0? Supabase? None yet?
- How long has it been in use?
- Happy with it or want to change?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 4. What authentication methods?
- Email/password?
- Social login (Google, GitHub, etc.)?
- Magic links?
- Phone/SMS?
- Which ones are actually used vs just planned?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 5. Where does auth happen?
- Client-side only?
- Server-side validation?
- Both?
- API middleware?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## User Flows

### 6. Sign up flow
- Simple email/password form?
- Multi-step registration?
- Email verification required?
- Any custom fields (name, company, phone)?
- Terms of service acceptance?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 7. Sign in flow
- Just email/password?
- "Remember me" option?
- Redirect after login (dashboard, home, last page)?
- Any MFA/2FA?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 8. Password reset
- In-app or email link to external page?
- Required or nice-to-have?
- How often do users actually use it?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 9. Sign out
- Simple sign out button?
- Redirect after sign out?
- Clear all sessions/tokens?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## UI & UX

### 10. What UI library/components?
- Custom components?
- Material-UI, Ant Design, shadcn/ui, Chakra?
- Must match existing design system?
- Can you swap UI components easily?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 11. What notification system?
- Toast notifications (which library)?
- Modals/dialogs?
- Console logs only?
- None?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 12. Login page style
- Dedicated login page?
- Modal/dialog?
- Sidebar?
- Embedded in layout?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 13. Branding requirements
- Custom logo/colors?
- White-label (different per tenant)?
- Standard/consistent across projects?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Protected Routes

### 14. What needs protection?
- Entire app (dashboard)?
- Specific pages only?
- API routes?
- Mix of public and protected?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 15. Redirect behavior
- Where to redirect unauthenticated users?
- Remember intended destination?
- Different redirects for different routes?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 16. Loading states
- Show spinner during auth check?
- Blank screen?
- Skeleton UI?
- Flash of wrong content okay?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Authorization (Roles & Permissions)

### 17. Do you need roles?
- Yes/No for each project
- If yes, what roles (admin, user, editor, viewer)?
- Are roles simple or complex?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 18. Where are roles stored?
- Database?
- JWT claims?
- Firebase custom claims?
- External service?
- Don't exist yet?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 19. What do roles control?
- Page access?
- UI element visibility?
- API endpoint access?
- Data filtering (row-level security)?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 20. How are roles assigned?
- Admin assigns manually?
- Auto-assigned on signup?
- Self-service (user picks)?
- Invite-based?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Backend Integration

### 21. What backend?
- Express? Next.js API routes? Separate service?
- Same codebase as frontend or separate?
- REST? GraphQL? tRPC?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 22. Token validation
- Where does it happen (frontend, backend, both)?
- What token format (JWT, session cookie, custom)?
- Token refresh needed?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 23. Database
- What database (PostgreSQL, MySQL, MongoDB, Firestore)?
- Store user data locally or rely on auth provider?
- Any user profile data beyond auth?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 24. API protection
- All APIs require auth?
- Some public endpoints?
- Rate limiting per user?
- Different permissions per endpoint?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Session Management

### 25. Session duration
- Stay logged in forever?
- Expire after time (how long)?
- Sliding expiration?
- Different per project?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 26. Multi-device
- Can user be logged in on multiple devices?
- Need to log out all sessions?
- See active sessions?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 27. Token storage
- localStorage? sessionStorage? cookies?
- HttpOnly cookies?
- Secure/SameSite flags?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Developer Experience

### 28. Testing
- Mock auth for tests?
- Test accounts needed?
- E2E test requirements?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 29. Local development
- Use production auth or separate?
- Emulators (Firebase)?
- Easy to set up for new devs?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 30. Environment differences
- Dev vs staging vs production configs?
- Different auth providers per environment?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Unique Requirements

### 31. Special features needed?
- Email verification?
- Account deletion?
- Profile photo upload?
- Impersonation (admin as user)?
- Account linking (merge accounts)?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 32. Compliance/Security
- GDPR requirements?
- HIPAA or other regulations?
- Audit logging needed?
- Password strength requirements?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 33. Integration with other services
- Stripe (payment)?
- SendGrid (emails)?
- Analytics (track auth events)?
- Webhooks on auth events?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Migration & Adoption

### 34. Existing users
- Do you have existing users to migrate?
- How many users per project?
- Can you migrate gradually?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 35. Timeline
- When do you need this?
- Can you update all 4 projects at once?
- Or roll out gradually?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 36. Team
- How many developers?
- Comfort level with auth concepts?
- Preference for simple vs flexible?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Pain Points

### 37. What's frustrating about current auth?
- Hard to maintain?
- Inconsistent across projects?
- Missing features?
- Too complex?
- Security concerns?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 38. What would make auth better?
- Less code duplication?
- Easier to customize?
- Better error handling?
- Clearer documentation?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

### 39. What must not break?
- Existing user sessions?
- Current user data?
- API integrations?
- Production uptime?

**Project 1:**  
**Project 2:**  
**Project 3:**  
**Project 4:**  

---

## Analysis Summary

After completing the questionnaire, create a comparison table:

| Category | Project 1 | Project 2 | Project 3 | Project 4 | Pattern |
|----------|-----------|-----------|-----------|-----------|---------|
| Framework | | | | | |
| Auth Provider | | | | | |
| Needs Roles | | | | | |
| UI Library | | | | | |
| Notification System | | | | | |
| Backend | | | | | |
| ... | | | | | |

### Pattern Key:
- ✅ **Same across all** → Must be in shared package (core feature)
- 🔄 **Varies but predictable** → Make configurable (config option)
- ❌ **Completely different** → Don't try to share (project-specific)

### Recommendations:

Based on the patterns identified:

**What to share (common across all projects):**
- 

**What to make configurable (varies between projects):**
- 

**What to leave project-specific (too different to share):**
- 

**Suggested package structure:**
- 

**Implementation priority:**
1. 
2. 
3. 

---

## Next Steps

1. Complete this questionnaire for all projects
2. Identify clear patterns in the summary
3. Design package boundaries based on patterns
4. Start with simplest common functionality
5. Build proof of concept with one project
6. Iterate and expand based on learnings
