# Multi-Party Chat System - Implementation Plan

**Created:** October 24, 2025  
**Updated:** October 24, 2025 (Technical Efficiencies Applied)  
**Status:** Planning Phase - Ready for Approval  
**Estimated Effort:** **8-9 hours** (full-featured with technical optimizations)

## Executive Summary

Implement a real-time, multi-party chat system to enable direct communication between:
- **Oracare** (client) ↔ Axiom team
- **Manufacturer** ↔ Axiom team
- **Internal team members** within Axiom

The system will feature a floating chat widget (Intercom-style) integrated seamlessly into the existing Oracare Fulfillment dashboard, leveraging existing Replit Auth for authentication and PostgreSQL for message persistence.

**⚠️ IMPLEMENTATION APPROACH:**
- **Full-Featured Implementation:** ALL features included (typing indicators, read receipts, email notifications, etc.)
- **Technical Efficiencies Applied:** Leveraging existing auth.js, pg_utils, simplified database architecture
- **Timeline: 8-9 hours** (down from 9-12 hours via technical optimizations, no feature deferrals)

**See Documentation:**
- [`CHAT_SYSTEM_GAP_ANALYSIS.md`](CHAT_SYSTEM_GAP_ANALYSIS.md) - 14 critical gaps identified
- [`CHAT_SYSTEM_TECHNICAL_EFFICIENCIES.md`](CHAT_SYSTEM_TECHNICAL_EFFICIENCIES.md) - 4 optimizations saving 3.75 hours

---

## Use Case & Requirements

### Primary Use Cases
1. **Client Communication**: Oracare team asks questions about orders, shipments, inventory
2. **Manufacturer Coordination**: Manufacturer updates on product availability, lot changes, shipping delays
3. **Internal Collaboration**: Axiom team coordinates on fulfillment operations
4. **Order-Specific Threads**: Discussions tied to specific orders, SKUs, or shipments

### Key Requirements (ALL INCLUDED - No Deferrals)
- ✅ Real-time messaging (instant delivery via WebSockets)
- ✅ 1-on-1 direct messages
- ✅ Team channels (#oracare-team, #manufacturer, #internal)
- ✅ Message history (last 50 messages per conversation)
- ✅ Floating widget accessible from all pages (Intercom-style)
- ✅ Works with existing Replit Auth (no additional login)
- ✅ Mobile responsive (iOS + Android)
- ✅ Typing indicators ("User is typing...")
- ✅ Online/offline presence (green dot indicators)
- ✅ Read receipts (message read tracking)
- ✅ Unread badge counts
- ✅ Email notifications when offline (via SendGrid)
- ✅ Role-based channel visibility (Admin/Viewer permissions)

---

## Decision: Custom Chat vs. Slack Integration

### Why Custom Chat Was Chosen

| Factor | Custom Chat | Slack Integration |
|--------|-------------|-------------------|
| **Login** | Uses existing Replit Auth | Requires separate Slack accounts |
| **Cost** | Free (6-8 hrs dev) | $7.25/user/month (Standard plan) |
| **Integration** | Seamless with dashboard | External tool, context switching |
| **Data Control** | Full ownership in PostgreSQL | Data stored with Slack |
| **User Experience** | Built into existing workflow | Requires learning Slack |
| **Order Linking** | Direct links to order details | Manual copy/paste |

**Verdict:** Custom chat provides better UX, lower cost, and tighter integration with existing fulfillment workflows.

---

## Technical Architecture

### Tech Stack
- **Backend**: Flask-SocketIO (WebSocket server)
- **Database**: PostgreSQL (existing) + 3 new tables
- **Frontend**: Socket.IO client library (JavaScript)
- **Auth**: Existing Replit Auth system
- **Server**: Eventlet (async worker for WebSockets)

### Database Schema

#### Table 1: `chat_messages`
```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    read_by JSONB DEFAULT '[]',
    deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_conversation_timestamp (conversation_id, timestamp),
    INDEX idx_sender (sender_id)
);
```

#### Table 2: `chat_conversations`
```sql
CREATE TABLE chat_conversations (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL CHECK (type IN ('direct', 'channel', 'order_thread')),
    name VARCHAR(100),
    participants JSONB NOT NULL,
    order_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_type (type),
    INDEX idx_order_number (order_number)
);
```

#### Table 3: `chat_presence`
```sql
CREATE TABLE chat_presence (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'offline' CHECK (status IN ('online', 'away', 'offline')),
    last_seen TIMESTAMP DEFAULT NOW(),
    socket_id VARCHAR(100)
);
```

---

## Implementation Phases

### Phase 1: Backend Setup (2.25 hours - with technical efficiencies)

**⚠️ CRITICAL PRE-REQUISITES (GAP-001, GAP-002):**
1. **Install Flask-SocketIO and dependencies**
   Add to `requirements.txt`:
   ```txt
   flask-socketio==5.3.6
   python-socketio==5.11.0
   eventlet==0.35.2
   ```
   Then run: `pip install -r requirements.txt`

2. **Switch to Eventlet Server (CRITICAL)**
   Modify `app.py` (end of file):
   ```python
   if __name__ == '__main__':
       import eventlet
       eventlet.monkey_patch()
       socketio.run(app, host='0.0.0.0', port=5000)
   ```
   
   **Why:** Flask dev server CANNOT handle WebSocket connections. This is a blocker.

**Tasks:**
3. Create chat service functions: `src/services/chat_service.py`
   - **EFFICIENCY:** Use existing `pg_utils.execute_query()` instead of custom service class
   - Message CRUD operations
   - Conversation management
   - Presence tracking (stored in `users` table - no separate table needed)

4. Add WebSocket event handlers to `app.py`
   - `connect` / `disconnect` with auth guards
   - `send_message` with role-based permissions
   - `join_conversation`
   - `typing_indicator` - Real-time typing status
   - `mark_read` - Update read receipts
   - `presence_update` - Online/offline status

5. Configure SocketIO with CORS for Replit iframe:
   ```python
   socketio = SocketIO(app, 
                      cors_allowed_origins="*",
                      async_mode='eventlet',
                      engineio_logger=False)
   ```

**Deliverables:**
- ✅ Dependencies installed
- ✅ Eventlet server running (test with: `curl http://localhost:5000`)
- ✅ SocketIO initialization complete
- ✅ Authentication guards functional
- ✅ Database-backed presence system working

---

### Phase 2: Database & API (1.5 hours - with technical efficiencies)

**Database Migration Strategy:**

**Tasks:**
1. **Create migration script** `migrations/001_create_chat_tables.sql`:
   ```sql
   -- chat_conversations table
   CREATE TABLE IF NOT EXISTS chat_conversations (
       id SERIAL PRIMARY KEY,
       type VARCHAR(20) NOT NULL CHECK (type IN ('direct', 'channel', 'order_thread')),
       name VARCHAR(100),
       participants JSONB NOT NULL,
       order_number VARCHAR(50),
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_chat_conversations_type ON chat_conversations(type);
   CREATE INDEX idx_chat_conversations_order ON chat_conversations(order_number);
   
   -- chat_messages table (with read receipts and soft delete)
   CREATE TABLE IF NOT EXISTS chat_messages (
       id SERIAL PRIMARY KEY,
       content TEXT NOT NULL,
       sender_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
       timestamp TIMESTAMP DEFAULT NOW(),
       read_by JSONB DEFAULT '[]',  -- Array of user IDs who read the message
       deleted BOOLEAN DEFAULT FALSE,  -- Soft delete for message history
       is_typing BOOLEAN DEFAULT FALSE  -- For typing indicators
   );
   
   CREATE INDEX idx_chat_messages_conversation ON chat_messages(conversation_id, timestamp DESC);
   CREATE INDEX idx_chat_messages_sender ON chat_messages(sender_id);
   CREATE INDEX idx_chat_messages_unread ON chat_messages(conversation_id) WHERE deleted = FALSE;
   
   -- EFFICIENCY: Add presence columns to existing users table (no separate table)
   ALTER TABLE users 
   ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE,
   ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT NOW(),
   ADD COLUMN IF NOT EXISTS socket_id VARCHAR(100);
   
   CREATE INDEX IF NOT EXISTS idx_users_online ON users(is_online);
   ```

2. **Execute migration** using `execute_sql_tool` on development database
3. **Verify schema** with:
   ```sql
   SELECT table_name, column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name IN ('chat_conversations', 'chat_messages', 'chat_presence');
   ```

4. Create REST API endpoints:
   - `GET /api/chat/conversations` - List all conversations for user (filtered by role - GAP-009)
   - `GET /api/chat/messages/<conversation_id>` - Get message history
   - `POST /api/chat/conversations` - Start new conversation
   - `POST /api/chat/conversations/<id>/mark_read` - Mark messages as read

5. Integrate with existing Replit Auth middleware (reuse `@login_required` pattern)

6. Seed initial channels with role visibility (GAP-009):
   ```sql
   INSERT INTO chat_conversations (type, name, participants)
   VALUES 
       ('channel', '#oracare-team', '["all"]'),
       ('channel', '#manufacturer', '["all"]'),
       ('channel', '#internal', '["admin"]');  -- Admin-only
   ```

**Deliverables:**
- ✅ 2 tables created + `users` table extended (with foreign keys)
- ✅ Migration tested on dev database (zero data loss)
- ✅ Full message history retrieval working
- ✅ Conversation creation and management functional
- ✅ Protected endpoints with role-based access
- ✅ Channel visibility enforced by role
- ✅ Read receipt tracking functional
- ✅ Typing indicator support in schema

---

### Phase 3: Chat UI Component (2 hours - full-featured)

**Tasks:**
1. Create floating chat widget: `static/js/chat-widget.js`
   - Minimizable panel in bottom-right corner (Intercom-style)
   - Badge showing unread count (red circle with number)
   - Conversation list view (with avatars)
   - Message thread view (with timestamps)
   - Input box with send button
   - Typing indicator display ("John is typing...")
   - Read receipts (checkmarks)
   - Online/offline presence indicators (green dots)

2. Create CSS: `static/css/chat-widget.css`
   - Professional styling matching Oracare blue (#2B7DE9) theme
   - Mobile responsive design (full-screen on mobile)
   - Dark mode support (navy glass effect)
   - Smooth animations (slide-in, fade)

3. Conversation types UI:
   - Direct message selector (user dropdown with online status)
   - Channel selector (#oracare-team, #manufacturer, #internal)
   - "New Conversation" button
   - Search conversations

**Deliverables:**
- ✅ Functional chat widget visible on all pages
- ✅ Message list with timestamps, usernames, and avatars
- ✅ Send/receive messages in real-time (<500ms latency)
- ✅ Typing indicators working
- ✅ Read receipts displaying
- ✅ Unread badge counts accurate
- ✅ Online/offline status indicators
- ✅ Mobile responsive (iOS + Android tested)

---

### Phase 4: Integration & Email Notifications (1.5 hours)

**Tasks:**
1. Add Socket.IO client library to all 15 HTML pages (via CDN):
   ```html
   <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
   <script src="/static/js/chat-widget.js"></script>
   ```

2. **EFFICIENCY:** Reuse existing `auth.js` infrastructure
   ```javascript
   // Use window.currentUser already loaded by auth.js (no duplicate API calls)
   function initChat() {
       if (!window.currentUser) return;
       renderChatWidget(window.currentUser, window.isAdmin);
   }
   ```

3. Implement role-based permissions:
   - Viewers can send messages in #oracare-team, #manufacturer
   - Only admins can access #internal channel
   - Admin-only channel creation

4. Add typing indicators:
   - Emit `typing` event on keypress
   - Display "User is typing..." in conversation
   - Auto-clear after 3 seconds of inactivity

5. Add online/offline presence:
   - Update `users.is_online` on connect/disconnect
   - Show green dot next to online users
   - Display "last seen" timestamp for offline users

6. Add unread badge counts:
   - Query `chat_messages.read_by` JSONB column
   - Show red badge on chat icon
   - Update in real-time as messages arrive

7. Add notification sound (subtle ping on new message)

8. **Email notifications** (via existing SendGrid integration):
   - Send email when user receives message while offline
   - Batch notifications (max 1 email per 5 minutes)
   - Include message preview and sender name
   - "Reply directly in dashboard" link

**Order Integration Ideas (Future Enhancement):**
- Add "Chat about this order" button on Orders Inbox page
- Automatically create order-specific thread
- Link order number in chat messages

**Deliverables:**
- ✅ Chat widget on all 15+ dashboard pages
- ✅ **EFFICIENCY:** Seamless auth.js integration (zero duplicate code)
- ✅ Real-time presence indicators (green dots)
- ✅ Typing indicators functional
- ✅ Unread badge counts working
- ✅ Role-based channel visibility enforced
- ✅ Viewer vs Admin permissions tested
- ✅ Email notifications working (SendGrid integration)
- ✅ Notification batching preventing spam

---

### Phase 5: Testing & Polish (2-2.5 hours - comprehensive)

**⚠️ CRITICAL TESTS (GAP-013):**

**Tasks:**
1. **Error handling** (GAP-013):
   - Add `@socketio.on_error_default` handler
   - Add comprehensive logging
   - Test error recovery scenarios

2. **Multi-user real-time messaging**:
   - Open 3+ browser tabs with different users
   - Verify instant message delivery (<500ms)
   - Test typing indicators
   - Test presence updates

3. **Server restart resilience**:
   - Stop Flask server (`Ctrl+C`)
   - Restart server
   - Verify automatic reconnection
   - Check presence recovery

4. **WebSocket reconnection testing** (GAP-013):
   - Simulate network drop (disable WiFi for 5 seconds)
   - Verify automatic reconnection
   - Check message queue recovery

5. **Mobile responsiveness** (GAP-014):
   - Test on iPhone Safari
   - Test on Chrome Android
   - Verify floating widget doesn't cover critical UI
   - Test keyboard interactions

6. **Cross-browser testing**:
   - Chrome, Firefox, Safari, Edge
   - Verify WebSocket fallback mechanisms

7. **Message persistence**:
   - Send messages
   - Refresh page
   - Verify history loads correctly

8. **Performance testing**:
   - Load 100+ messages in conversation
   - Test scroll performance
   - Monitor memory usage

9. **Security testing**:
   - Verify viewer can't access #internal channel
   - Verify users can't access unauthorized conversations
   - Test SQL injection prevention in message content

10. **Workflow regression testing**:
    - Verify all 7 workflows still running
    - Check dashboard loads normally
    - Test existing API endpoints

**Deliverables:**
- ✅ Production-ready chat system
- ✅ Zero critical bugs
- ✅ Error handling comprehensive
- ✅ Mobile responsive (iOS + Android)
- ✅ WebSocket reconnection tested
- ✅ Server restart recovery working
- ✅ Load tested (50+ concurrent connections)
- ✅ All 7 workflows running (zero regressions)
- ✅ Documented in replit.md

---

## File Structure

```
oracare-fulfillment/
├── app.py                              # Add SocketIO initialization
├── src/
│   ├── models/
│   │   └── chat_models.py              # NEW: Chat database models
│   ├── services/
│   │   └── chat_service.py             # NEW: Chat business logic
├── static/
│   ├── js/
│   │   └── chat-widget.js              # NEW: Chat UI component
│   ├── css/
│   │   └── chat-widget.css             # NEW: Chat styling
├── templates/
│   └── chat_widget.html                # NEW: Chat widget HTML template
├── docs/
│   └── features/
│       └── CHAT_SYSTEM_IMPLEMENTATION_PLAN.md  # This document
```

---

## Code Snippets Preview

### Flask-SocketIO Event Handler (app.py)
```python
from flask_socketio import SocketIO, emit, join_room

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@socketio.on('send_message')
@login_required
def handle_send_message(data):
    conversation_id = data['conversation_id']
    content = data['message']
    sender_id = current_user.id
    
    # Save to database
    message = chat_service.create_message(sender_id, conversation_id, content)
    
    # Broadcast to all participants in conversation
    emit('new_message', {
        'id': message['id'],
        'sender': message['sender_username'],
        'content': content,
        'timestamp': message['timestamp']
    }, room=f'conversation_{conversation_id}', broadcast=True)
```

### Chat Widget UI (chat-widget.js)
```javascript
const socket = io();

socket.on('new_message', (data) => {
    appendMessage(data.sender, data.content, data.timestamp);
    updateUnreadCount();
    playNotificationSound();
});

function sendMessage() {
    const message = document.getElementById('chat-input').value;
    socket.emit('send_message', {
        conversation_id: currentConversationId,
        message: message
    });
}
```

---

## Security Considerations

1. **Authentication**: All WebSocket connections require valid Replit Auth session
2. **Authorization**: Users can only access conversations they're participants in
3. **Input Validation**: Sanitize all message content to prevent XSS
4. **Rate Limiting**: Prevent spam by limiting messages per minute per user
5. **Encryption**: Use HTTPS/WSS for WebSocket connections in production
6. **Data Privacy**: Message deletion properly removes from all participants

---

## Features Included in This Implementation ✅

**Core Messaging:**
- ✅ Real-time messaging via WebSockets
- ✅ 1-on-1 direct messages
- ✅ Team channels (#oracare-team, #manufacturer, #internal)
- ✅ Message history (last 50 per conversation)

**User Experience:**
- ✅ Floating widget (Intercom-style, bottom-right)
- ✅ Typing indicators ("User is typing...")
- ✅ Read receipts (message read tracking)
- ✅ Online/offline presence (green dots)
- ✅ Unread badge counts
- ✅ Mobile responsive (iOS + Android)
- ✅ Dark mode support

**Notifications:**
- ✅ In-app notification sound
- ✅ Email notifications when offline (SendGrid)
- ✅ Notification batching (max 1 email/5 min)

**Security & Permissions:**
- ✅ Replit Auth integration
- ✅ Role-based channel access (Admin/Viewer)
- ✅ Protected API endpoints

## Future Enhancements (Post-MVP)

- 📎 **File Attachments**: Upload images, PDFs, CSV files (2-3 hours)
- 🔍 **Full-Text Search**: Search across all message history (2 hours)
- 🔔 **Custom Notifications**: Mentions (@username), keywords (1 hour)
- 📊 **Analytics Dashboard**: Message volume, response times (3 hours)
- 🤖 **Chatbot Integration**: Auto-responses to common questions (4-5 hours)
- 📱 **Mobile App**: React Native or PWA for mobile access (20+ hours)

---

## Timeline Summary

| Phase | Description | Time | Dependencies |
|-------|-------------|------|--------------|
| Phase 1: Backend Setup | Flask-SocketIO, eventlet, pg_utils | **2.25 hrs** | PostgreSQL, Flask |
| Phase 2: Database & API | 2 tables + users extension, REST APIs | **1.5 hrs** | Phase 1 complete |
| Phase 3: Chat UI | Floating widget, all features (typing, read receipts) | **2 hrs** | Phase 2 complete |
| Phase 4: Integration | Auth.js reuse, email notifications | **1.5 hrs** | Phase 3 complete |
| Phase 5: Testing & Polish | All features, mobile, error handling | **2-2.5 hrs** | All phases complete |
| **TOTAL** | **Full-featured with technical efficiencies** | **8-9 hrs** | - |

**Timeline Optimizations Applied:**
- ✅ Reuse existing auth.js infrastructure (-1 hour)
- ✅ Leverage pg_utils database helpers (-45 minutes)
- ✅ Simplified DB architecture (users table extension) (-30 minutes)
- ✅ Parallel development workflow (-1 hour)
- **Total savings: 3.75 hours** (from 12 hrs → 8-9 hrs)
- **ALL features included** (no deferrals)

---

## Success Metrics

After implementation, success will be measured by:
- ✅ Real-time message delivery < 500ms latency
- ✅ Zero message loss (100% persistence to PostgreSQL)
- ✅ Mobile responsive on iOS and Android
- ✅ Zero authentication regressions
- ✅ All 7 workflows continue running without errors
- ✅ Positive user feedback from Oracare and Manufacturer

---

## Next Steps

1. **Get Approval**: Review this plan with stakeholders
2. **Schedule Development**: Block 1-2 days for focused implementation
3. **Begin Phase 1**: Install dependencies and create database schema
4. **Iterate**: Build incrementally, test frequently

---

## Pre-Implementation Checklist

**Before starting Phase 1, verify:**

- [ ] Gap analysis reviewed (14 critical gaps identified and addressed)
- [ ] Technical efficiencies understood (4 optimizations applied)
- [ ] Stakeholders approve 8-9 hour timeline (full-featured implementation)
- [ ] Database backup available (just in case)
- [ ] Development environment ready for testing
- [ ] All 7 workflows currently running without errors ✅
- [ ] SendGrid configured for email notifications

**Technical Efficiencies to Apply:**
- [ ] **EFFICIENCY-001**: Reuse existing auth.js (window.currentUser)
- [ ] **EFFICIENCY-002**: Leverage pg_utils.execute_query()
- [ ] **EFFICIENCY-003**: Extend users table (no separate presence table)
- [ ] **EFFICIENCY-004**: Parallel development workflow

**Critical Pre-requisites:**
- [ ] Install dependencies: flask-socketio, python-socketio, eventlet
- [ ] Switch to eventlet server (Flask dev server won't work)
- [ ] Migration script prepared with all features (read receipts, typing, etc.)

---

## Implementation Summary

**Timeline:** 8-9 hours (full-featured)  
**Features:** ALL included (typing, read receipts, email notifications, presence, etc.)  
**Optimizations:** 4 technical efficiencies applied (3.75 hours saved)  
**Risk Level:** Low (leveraging proven existing infrastructure)  

**This implementation includes:**
- Real-time messaging with all UX features
- Email notifications via SendGrid
- Role-based permissions
- Mobile responsive design
- Comprehensive testing

**Nothing deferred** - this is a complete, production-ready chat system.

---

## Related Documentation

- **[Chat System Gap Analysis](CHAT_SYSTEM_GAP_ANALYSIS.md)** - 14 critical gaps identified and mitigated
- **[Chat System Technical Efficiencies](CHAT_SYSTEM_TECHNICAL_EFFICIENCIES.md)** - 4 optimizations saving 3.75 hours
- [Chat System Efficiency Analysis](CHAT_SYSTEM_EFFICIENCY_ANALYSIS.md) - Complete efficiency breakdown
- [Replit Auth Implementation Plan](REPLIT_AUTH_IMPLEMENTATION_PLAN_REVISED.md) - Similar brownfield approach
- [Production Incident Log](../PRODUCTION_INCIDENT_LOG.md)
- [Project Journal](../PROJECT_JOURNAL.md)
