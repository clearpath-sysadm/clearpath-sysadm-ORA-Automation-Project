# Multi-Party Chat System - Implementation Plan

**Created:** October 24, 2025  
**Updated:** October 24, 2025 (Gap Analysis Complete)  
**Status:** Planning Phase - Ready for Approval  
**Estimated Effort:** ~~6-8 hours~~ **9-12 hours** (revised after gap analysis)

## Executive Summary

Implement a real-time, multi-party chat system to enable direct communication between:
- **Oracare** (client) ↔ Axiom team
- **Manufacturer** ↔ Axiom team
- **Internal team members** within Axiom

The system will feature a floating chat widget (Intercom-style) integrated seamlessly into the existing Oracare Fulfillment dashboard, leveraging existing Replit Auth for authentication and PostgreSQL for message persistence.

**⚠️ CRITICAL FINDINGS FROM GAP ANALYSIS:**
- Current Flask development server cannot handle WebSockets (requires eventlet server)
- Missing dependencies: flask-socketio, python-socketio, eventlet
- Database migration requires careful planning to avoid data loss
- Revised timeline: **9-12 hours** (was 6-8 hours)

**See:** [`CHAT_SYSTEM_GAP_ANALYSIS.md`](CHAT_SYSTEM_GAP_ANALYSIS.md) for complete 14-point gap analysis.

---

## Use Case & Requirements

### Primary Use Cases
1. **Client Communication**: Oracare team asks questions about orders, shipments, inventory
2. **Manufacturer Coordination**: Manufacturer updates on product availability, lot changes, shipping delays
3. **Internal Collaboration**: Axiom team coordinates on fulfillment operations
4. **Order-Specific Threads**: Discussions tied to specific orders, SKUs, or shipments

### Key Requirements
- ✅ Real-time messaging (instant delivery via WebSockets)
- ✅ 1-on-1 direct messages
- ✅ Team channels (#oracare-team, #manufacturer, #internal)
- ✅ Message history with full-text search
- ✅ Floating widget accessible from all pages
- ✅ Works with existing Replit Auth (no additional login)
- ✅ Mobile responsive
- ✅ Typing indicators and online presence
- ✅ Optional: Email notifications when offline

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

### Phase 1: Backend Setup (~~2 hours~~ **3 hours** - revised)

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
3. Create database models in new file: `models/chat_models.py` (not `src/models/` - see GAP-007)
4. Create chat service: `src/services/chat_service.py`
   - Message CRUD operations using psycopg2 (matches existing pattern)
   - Conversation management
   - Database-backed presence tracking (NO in-memory state - see GAP-006)
5. Add WebSocket event handlers to `app.py`
   - `connect` / `disconnect` with auth guards (GAP-008)
   - `send_message` with role-based permissions (GAP-009)
   - `join_conversation`
   - `typing_indicator`
   - `mark_read`
6. Configure SocketIO with CORS for Replit iframe (GAP-005):
   ```python
   socketio = SocketIO(app, 
                      cors_allowed_origins="*",
                      async_mode='eventlet')
   ```

**Deliverables:**
- ✅ Dependencies installed
- ✅ Eventlet server running (test with: `curl http://localhost:5000`)
- ✅ SocketIO initialization complete
- ✅ Authentication guards functional
- ✅ Database-backed presence system working

---

### Phase 2: Database & API (~~1 hour~~ **2 hours** - revised)

**⚠️ CRITICAL: Database Migration Strategy (GAP-003, GAP-004)**

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
   
   -- chat_messages table
   CREATE TABLE IF NOT EXISTS chat_messages (
       id SERIAL PRIMARY KEY,
       content TEXT NOT NULL,
       sender_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
       timestamp TIMESTAMP DEFAULT NOW(),
       read_by JSONB DEFAULT '[]',
       deleted BOOLEAN DEFAULT FALSE
   );
   
   CREATE INDEX idx_chat_messages_conversation ON chat_messages(conversation_id, timestamp DESC);
   CREATE INDEX idx_chat_messages_sender ON chat_messages(sender_id);
   
   -- chat_presence table
   CREATE TABLE IF NOT EXISTS chat_presence (
       user_id VARCHAR PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
       status VARCHAR(20) DEFAULT 'offline' CHECK (status IN ('online', 'away', 'offline')),
       last_seen TIMESTAMP DEFAULT NOW(),
       socket_id VARCHAR(100)
   );
   
   CREATE INDEX idx_chat_presence_status ON chat_presence(status);
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
- ✅ 3 tables created with proper foreign keys
- ✅ Migration tested on dev database (zero data loss)
- ✅ Full message history retrieval working
- ✅ Conversation creation and management functional
- ✅ Protected endpoints with role-based access
- ✅ Channel visibility enforced by role

---

### Phase 3: Chat UI Component (2 hours)

**Tasks:**
1. Create floating chat widget: `static/js/chat-widget.js`
   - Minimizable panel in bottom-right corner
   - Badge showing unread count
   - Conversation list view
   - Message thread view
   - Input box with send button
2. Create CSS: `static/css/chat-widget.css`
   - Professional styling matching Oracare blue theme
   - Mobile responsive design
   - Dark mode support
3. Conversation types UI:
   - Direct message selector (user dropdown)
   - Channel selector (#oracare-team, etc.)
   - "New Conversation" button

**Deliverables:**
- ✅ Functional chat widget visible on all pages
- ✅ Message list with timestamps and usernames
- ✅ Send/receive messages in real-time

---

### Phase 4: Integration & Features (~~1 hour~~ **1.5 hours** - revised)

**Tasks:**
1. Add Socket.IO client library to all HTML pages (via CDN):
   ```html
   <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
   <script src="/static/js/chat-widget.js"></script>
   ```

2. Initialize chat widget on page load (integrate with existing `auth.js`)

3. Connect to existing auth system (use `current_user` data from `/api/auth/status`)

4. **Implement role-based permissions (GAP-009)**:
   ```javascript
   if (currentUser.role === 'viewer') {
       // Hide #internal channel
       // Allow sending messages in other channels
   }
   ```

5. Add typing indicators (emit `typing` event on keypress)

6. Add online/offline presence (database-backed, not in-memory)

7. Add unread badge counts (query `chat_messages.read_by` JSONB column)

8. Add notification sound (optional)

**Order Integration Ideas (Future Enhancement):**
- Add "Chat about this order" button on Orders Inbox page
- Automatically create order-specific thread
- Link order number in chat messages

**Deliverables:**
- ✅ Chat widget on all 15+ dashboard pages
- ✅ Seamless authentication integration
- ✅ Real-time presence indicators
- ✅ Role-based channel visibility enforced
- ✅ Viewer vs Admin permissions tested

---

### Phase 5: Testing & Polish (~~1-2 hours~~ **2-3 hours** - revised)

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

## Future Enhancements (Optional)

- 📎 **File Attachments**: Upload images, PDFs, CSV files
- 📧 **Email Notifications**: Alert offline users via SendGrid
- 🔍 **Full-Text Search**: Search across all message history
- 🔔 **Custom Notifications**: Mentions (@username), keywords
- 📊 **Analytics Dashboard**: Message volume, response times
- 🤖 **Chatbot Integration**: Auto-responses to common questions
- 📱 **Mobile App**: React Native or PWA for mobile access

---

## Timeline Summary

| Phase | Original | Revised | Dependencies |
|-------|----------|---------|--------------|
| Phase 1: Backend Setup | 2 hours | **3 hours** | PostgreSQL, Flask, eventlet |
| Phase 2: Database & API | 1 hour | **2 hours** | Phase 1 complete |
| Phase 3: Chat UI | 2 hours | **2 hours** | Phase 2 complete |
| Phase 4: Integration | 1 hour | **1.5 hours** | Phase 3 complete |
| Phase 5: Testing & Polish | 1-2 hours | **2-3 hours** | All phases complete |
| **TOTAL** | **6-8 hours** | **9-12 hours** | Gap analysis complete |

**Reason for Increase:** Gap analysis identified 14 critical gaps requiring additional implementation time:
- Server architecture change (Flask dev → eventlet)
- Database migration complexity
- Role-based access control
- Enhanced error handling and testing

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

- [ ] Gap analysis reviewed and understood
- [ ] Stakeholders approve 9-12 hour timeline (vs original 6-8)
- [ ] Database backup available (just in case)
- [ ] Development environment ready for testing
- [ ] All 7 workflows currently running without errors

**Critical Gaps to Address:**
- [ ] **GAP-001**: Dependencies added to requirements.txt
- [ ] **GAP-002**: Server architecture change planned
- [ ] **GAP-003**: Database migration script prepared
- [ ] **GAP-005**: CORS configuration understood
- [ ] **GAP-006**: Database-backed presence strategy clear
- [ ] **GAP-008**: Authentication integration approach defined
- [ ] **GAP-009**: Role-based permissions policy documented

---

## Related Documentation

- **[Chat System Gap Analysis](CHAT_SYSTEM_GAP_ANALYSIS.md)** - **READ FIRST** - 14 critical gaps identified
- [Replit Auth Implementation Plan](REPLIT_AUTH_IMPLEMENTATION_PLAN_REVISED.md)
- [Production Incident Log](../PRODUCTION_INCIDENT_LOG.md)
- [Project Journal](../PROJECT_JOURNAL.md)
