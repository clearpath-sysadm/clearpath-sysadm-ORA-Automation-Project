# Multi-Party Chat System - Implementation Plan

**Created:** October 24, 2025  
**Status:** Planning Phase  
**Estimated Effort:** 6-8 hours

## Executive Summary

Implement a real-time, multi-party chat system to enable direct communication between:
- **Oracare** (client) ↔ Axiom team
- **Manufacturer** ↔ Axiom team
- **Internal team members** within Axiom

The system will feature a floating chat widget (Intercom-style) integrated seamlessly into the existing Oracare Fulfillment dashboard, leveraging existing Replit Auth for authentication and PostgreSQL for message persistence.

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

### Phase 1: Backend Setup (2 hours)

**Tasks:**
1. Install Flask-SocketIO and dependencies
   ```bash
   pip install flask-socketio eventlet python-socketio
   ```
2. Create database models in new file: `src/models/chat_models.py`
3. Create chat service: `src/services/chat_service.py`
   - Message CRUD operations
   - Conversation management
   - Presence tracking
4. Add WebSocket event handlers to `app.py`
   - `connect` / `disconnect`
   - `send_message`
   - `join_conversation`
   - `typing_indicator`
   - `mark_read`

**Deliverables:**
- ✅ Database tables created
- ✅ API endpoints for message history
- ✅ Real-time message broadcasting working

---

### Phase 2: Database & API (1 hour)

**Tasks:**
1. Run database migrations to create 3 new tables
2. Create REST API endpoints:
   - `GET /api/chat/conversations` - List all conversations for user
   - `GET /api/chat/messages/<conversation_id>` - Get message history
   - `POST /api/chat/conversations` - Start new conversation
   - `POST /api/chat/conversations/<id>/mark_read` - Mark messages as read
3. Integrate with existing Replit Auth middleware
4. Seed initial channels: #oracare-team, #manufacturer, #internal

**Deliverables:**
- ✅ Full message history retrieval
- ✅ Conversation creation and management
- ✅ Protected endpoints with role-based access

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

### Phase 4: Integration & Features (1 hour)

**Tasks:**
1. Add Socket.IO client library to all HTML pages
2. Initialize chat widget on page load
3. Connect to existing auth system (use current_user data)
4. Add typing indicators
5. Add online/offline presence
6. Add unread badge counts
7. Add notification sound (optional)

**Order Integration Ideas (Future Enhancement):**
- Add "Chat about this order" button on Orders Inbox page
- Automatically create order-specific thread
- Link order number in chat messages

**Deliverables:**
- ✅ Chat widget on all 15+ dashboard pages
- ✅ Seamless authentication integration
- ✅ Real-time presence indicators

---

### Phase 5: Testing & Polish (1-2 hours)

**Tasks:**
1. Test multi-user real-time messaging
2. Test across different browsers
3. Test mobile responsiveness
4. Verify message persistence (refresh page, messages reload)
5. Test WebSocket reconnection on network interruptions
6. Performance testing (100+ messages in conversation)
7. Security testing (ensure users can't access unauthorized conversations)
8. Bug fixes and polish

**Deliverables:**
- ✅ Production-ready chat system
- ✅ Zero critical bugs
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

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Backend Setup | 2 hours | PostgreSQL, Flask |
| Phase 2: Database & API | 1 hour | Phase 1 complete |
| Phase 3: Chat UI | 2 hours | Phase 2 complete |
| Phase 4: Integration | 1 hour | Phase 3 complete |
| Phase 5: Testing & Polish | 1-2 hours | All phases complete |
| **TOTAL** | **6-8 hours** | - |

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

## Related Documentation

- [Replit Auth Implementation Plan](REPLIT_AUTH_IMPLEMENTATION_PLAN_REVISED.md)
- [Database Schema](../DATABASE_SCHEMA.md)
- [Production Incident Log](../PRODUCTION_INCIDENT_LOG.md)
- [Project Journal](../PROJECT_JOURNAL.md)
