# Server Logging & User Tracking Implementation Report

**Implementation Date:** December 2025 - January 2026  
**Status:** Complete  
**Version:** 1.0

---

## Executive Summary

This document provides a comprehensive technical reference for the Server Logging and User Tracking system implemented for the Oracare Fulfillment System. The system provides file-based logging with rotation, multi-dimensional filtering, user activity tracking, and an admin-only web interface for log analysis.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Implementation](#backend-implementation)
3. [Frontend Implementation](#frontend-implementation)
4. [User Tracking System](#user-tracking-system)
5. [API Endpoints](#api-endpoints)
6. [Configuration Options](#configuration-options)
7. [Log Format Specification](#log-format-specification)
8. [Filtering Capabilities](#filtering-capabilities)
9. [Files Modified](#files-modified)
10. [Lessons Learned](#lessons-learned)
11. [Known Issues & Limitations](#known-issues--limitations)
12. [Future Enhancements](#future-enhancements)

---

## 1. Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      SERVER LOGGING SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │   Flask App      │    │  Scheduled Jobs  │                   │
│  │   (app.py)       │    │  (src/*.py)      │                   │
│  └────────┬─────────┘    └────────┬─────────┘                   │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌────────────────────────────────────────────┐                 │
│  │         ServerLogger (Singleton)            │                 │
│  │         src/utils/server_logger.py          │                 │
│  │                                             │                 │
│  │  • RotatingFileHandler (10MB, 7 backups)   │                 │
│  │  • Console output                           │                 │
│  │  • User/role tracking                       │                 │
│  └────────────────────┬───────────────────────┘                 │
│                       │                                          │
│                       ▼                                          │
│  ┌────────────────────────────────────────────┐                 │
│  │           logs/app.log                      │                 │
│  │           + app.log.1 through app.log.7     │                 │
│  └────────────────────┬───────────────────────┘                 │
│                       │                                          │
│                       ▼                                          │
│  ┌────────────────────────────────────────────┐                 │
│  │         /api/admin/logs API                 │                 │
│  │         (Admin-only access)                 │                 │
│  └────────────────────┬───────────────────────┘                 │
│                       │                                          │
│                       ▼                                          │
│  ┌────────────────────────────────────────────┐                 │
│  │         logs.html (Web Interface)           │                 │
│  │         Admin-only Server Logs page         │                 │
│  └────────────────────────────────────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Logging Call** → Application code calls `server_logger.info()`, `.error()`, etc.
2. **Format & Write** → Logger formats message with timestamp, level, source, actor/role
3. **File Storage** → Written to `logs/app.log` with automatic rotation
4. **API Access** → `/api/admin/logs` reads, parses, and filters log entries
5. **Web Display** → `logs.html` renders filtered logs with syntax highlighting

---

## 2. Backend Implementation

### 2.1 ServerLogger Class (`src/utils/server_logger.py`)

**Design Pattern:** Singleton  
**File Size:** 355 lines

#### Class Structure

```python
class ServerLogger:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

#### Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `LOG_DIR` | `'logs'` | Directory for log files |
| `LOG_FILE` | `'app.log'` | Main log filename |
| `MAX_LOG_SIZE` | `10 * 1024 * 1024` (10MB) | Maximum size before rotation |
| `BACKUP_COUNT` | `7` | Number of rotated backup files |
| `DEFAULT_LOG_LEVEL` | `'INFO'` | Default logging level |

#### Logging Methods

All methods accept these parameters:
- `message: str` - The log message
- `source: str = 'app'` - Module/component source identifier
- `user: str = None` - Username who triggered the action
- `role: str = None` - User's role (admin/operations/viewer)

```python
def debug(self, message: str, source: str = 'app', user: str = None, role: str = None)
def info(self, message: str, source: str = 'app', user: str = None, role: str = None)
def warning(self, message: str, source: str = 'app', user: str = None, role: str = None)
def error(self, message: str, source: str = 'app', user: str = None, role: str = None, exc_info: bool = False)
def critical(self, message: str, source: str = 'app', user: str = None, role: str = None, exc_info: bool = False)
```

#### Actor Formatting

```python
def _format_actor(self, user: str = None, role: str = None) -> str:
    """Format actor string with optional role"""
    if user:
        if role:
            return f'<{user}|{role}>'
        return f'<{user}>'
    return '<system>'
```

**Examples:**
- Authenticated user with role: `<Nathan|admin>`
- Authenticated user without role: `<Nathan>`
- System/automated process: `<system>`

### 2.2 Log Reading Utilities

#### `read_logs()` Function

**Purpose:** Read, parse, and filter log entries

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | str | `'ALL'` | Filter by log level |
| `source` | str | `'ALL'` | Filter by source module |
| `category` | str | `'ALL'` | Filter by category |
| `search_pattern` | str | `None` | Regex search pattern |
| `last_n_lines` | int | `500` | Maximum lines to return |
| `hours_back` | int | `24` | Time window filter |

**Returns:**
```python
{
    'logs': [
        {
            'timestamp': '2025-01-07T12:30:45',
            'level': 'INFO',
            'source': 'ShipStation',
            'actor': 'Nathan',
            'role': 'admin',
            'message': 'Manual ShipStation sync triggered',
            'raw': 'full raw log line'
        },
        # ... more entries
    ],
    'stats': {
        'total_lines': 15420,
        'error_count': 12,
        'warning_count': 45,
        'info_count': 15200,
        'debug_count': 163,
        'file_size': 2548712,
        'displayed_count': 500
    }
}
```

#### Category Pattern Matching

The system supports category-based filtering using regex patterns:

```python
category_patterns = {
    'API': r'\[api\]|/api/|endpoint|request|response',
    'Database': r'\[database\]|\[db\]|postgres|sql|query|insert|update|delete',
    'ShipStation': r'\[shipstation\]|shipstation|order.*upload|sync',
    'Auth': r'\[auth\]|login|logout|session|token|permission',
    'Inventory': r'\[inventory\]|inventory|stock|lot|sku',
    'Scheduler': r'\[scheduler\]|\[cron\]|scheduled|polling|workflow',
    'Email': r'\[email\]|sendgrid|mail|notification',
    'Import': r'\[import\]|xml|google.*drive|import'
}
```

#### Log Line Parsing

Two regex patterns support both new and legacy log formats:

```python
# New format: timestamp - LEVEL - message
log_pattern_new = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(\w+)\s*-\s*(.*)$')

# Old format with logger name: timestamp - LEVEL - loggername - message
log_pattern_old = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(\w+)\s*-\s*\S+\s*-\s*(.*)$')
```

---

## 3. Frontend Implementation

### 3.1 Web Interface (`logs.html`)

**Location:** Root directory  
**File Size:** 788 lines  
**Access Control:** Admin-only (enforced via JavaScript and API)

#### UI Components

1. **Stats Grid** - Clickable cards showing:
   - Total Lines
   - Errors (red)
   - Warnings (yellow)
   - Info (blue)
   - File Size
   - Displayed Count

2. **Filter Controls**
   - Log Level dropdown
   - Category dropdown
   - Process dropdown (grouped by Reports, Workflows, Operations)
   - User dropdown (dynamically populated)
   - Lines limit dropdown
   - Hours Back dropdown
   - Search input with debounce

3. **Log Container**
   - Scrollable container (max-height: 600px)
   - Syntax-highlighted log lines
   - Level-based color coding with left border
   - Pre-wrap for multi-line messages and stack traces

4. **Action Buttons**
   - Auto-refresh toggle (5-second interval)
   - Download logs
   - Manual refresh

#### CSS Classes for Log Levels

```css
.log-line.ERROR {
    background: rgba(239, 68, 68, 0.2);
    border-left: 4px solid #ef4444;
}
.log-line.WARNING {
    background: rgba(245, 158, 11, 0.15);
    border-left: 4px solid #f59e0b;
}
.log-line.INFO {
    background: rgba(59, 130, 246, 0.1);
    border-left: 4px solid #3b82f6;
}
.log-line.DEBUG {
    background: rgba(139, 92, 246, 0.1);
    border-left: 4px solid #8b5cf6;
}
```

#### Key JavaScript Functions

| Function | Purpose |
|----------|---------|
| `checkAuth()` | Verify admin access, redirect non-admins |
| `loadLogs()` | Fetch and display logs from API |
| `updateStats(stats)` | Update statistics cards |
| `renderLogs(logs)` | Render log entries with formatting |
| `updateUserDropdown(logs)` | Dynamically populate user filter |
| `filterByLevel(level)` | Quick-filter by clicking stat card |
| `applyProcessFilter()` | Apply process-based search filter |
| `applyUserFilter()` | Apply user-based search filter |
| `toggleAutoRefresh()` | Start/stop 5-second auto-refresh |
| `downloadLogs()` | Trigger log file download |
| `debounceSearch()` | 300ms debounce for search input |
| `formatTimestamp(isoString)` | Convert to local timezone display |

### 3.2 Dynamic User Dropdown

The User filter dropdown is dynamically populated based on actual users found in the current log data:

```javascript
function updateUserDropdown(logs) {
    const userSelect = document.getElementById('filter-user');
    const currentValue = userSelect.value;
    
    // Collect unique users from logs
    const users = new Set();
    logs.forEach(log => {
        if (log.actor && log.actor !== 'system') {
            users.add(log.actor);
        }
    });
    
    // Rebuild options
    userSelect.innerHTML = '<option value="ALL">All Users</option><option value="system">System Only</option>';
    
    if (users.size > 0) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = 'Users';
        Array.from(users).sort().forEach(user => {
            const option = document.createElement('option');
            option.value = user;
            option.textContent = user;
            optgroup.appendChild(option);
        });
        userSelect.appendChild(optgroup);
    }
    
    // Restore selection if still valid
    if (currentValue) {
        userSelect.value = currentValue;
    }
}
```

---

## 4. User Tracking System

### 4.1 Authentication Integration

The system uses Replit Auth middleware to identify users:

**Correct Import Pattern:**
```python
from src.auth.middleware import get_current_user
```

**User Object Properties:**
- `user.is_authenticated` - Boolean authentication status
- `user.first_name` - User's first name
- `user.email` - User's email address
- `user.role` - User's role (admin/operations/viewer)

### 4.2 Implementation Pattern for Endpoints

All user-triggered endpoints follow this pattern:

```python
@app.route('/api/some_action', methods=['POST'])
def api_some_action():
    from src.utils.server_logger import get_logger
    server_logger = get_logger()
    
    # Get current user for logging
    user_name = "unknown"
    user_role = None
    try:
        from src.auth.middleware import get_current_user
        user = get_current_user()
        if user and user.is_authenticated:
            user_name = user.first_name or user.email or "unknown"
            user_role = user.role
    except:
        pass
    
    # Log the action with user context
    server_logger.info("Some action performed", source="Module", user=user_name, role=user_role)
    
    # ... rest of endpoint logic
```

### 4.3 Endpoints with User Tracking

| Endpoint | Source | Description |
|----------|--------|-------------|
| `/api/sync_shipstation` | ShipStation | Manual ShipStation sync trigger |
| `/api/tracking/compose_email` | Email | Email composition tracking |
| `/api/manual_order_conflicts/<id>/confirm_delete` | ShipStation | Conflict resolution - delete order |
| `/api/manual_order_conflicts/<id>/dismiss` | ShipStation | Conflict dismissal |
| `/api/reports/eod` | Reports | End of Day report generation |
| `/api/reports/eow` | Reports | End of Week report generation |
| `/api/reports/eom` | Reports | End of Month report generation |

### 4.4 System vs User Activity

**System Activity (`<system>`):**
- Scheduled workflows (XML import, ShipStation upload/sync, scanners)
- Background jobs
- Startup/shutdown events

**User Activity (`<Username|role>`):**
- Manual sync triggers
- Report generation (EOD/EOW/EOM)
- Conflict resolution actions
- Email composition

---

## 5. API Endpoints

### 5.1 GET `/api/admin/logs`

**Access:** Admin only

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | `ALL` | Log level filter |
| `category` | string | `ALL` | Category filter |
| `lastNLines` | integer | `500` | Max lines to return |
| `hoursBack` | integer | `24` | Time window |
| `searchPattern` | string | empty | Regex search pattern |

**Response:**
```json
{
    "success": true,
    "logs": [...],
    "stats": {
        "total_lines": 15420,
        "error_count": 12,
        "warning_count": 45,
        "info_count": 15200,
        "debug_count": 163,
        "file_size": 2548712,
        "displayed_count": 500
    }
}
```

### 5.2 GET `/api/admin/logs/download`

**Access:** Admin only

**Response:** Raw log file as text/plain download

---

## 6. Configuration Options

### 6.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Minimum log level to capture |

**Valid Log Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

### 6.2 Log Rotation Settings

| Setting | Value | Configurable |
|---------|-------|--------------|
| Max file size | 10 MB | Code constant |
| Backup count | 7 files | Code constant |
| Encoding | UTF-8 | Code constant |

---

## 7. Log Format Specification

### 7.1 Raw Log Format

```
{timestamp} - {LEVEL} - [{source}] <{actor}|{role}> {message}
```

**Examples:**
```
2025-01-07T14:32:15 - INFO - [ShipStation] <Nathan|admin> Manual ShipStation sync triggered
2025-01-07T14:30:00 - INFO - [Scheduler] <system> XML import started
2025-01-07T14:28:45 - ERROR - [Database] <system> Connection timeout after 30s
```

### 7.2 Parsed Log Structure

```json
{
    "timestamp": "2025-01-07T14:32:15",
    "level": "INFO",
    "source": "ShipStation",
    "actor": "Nathan",
    "role": "admin",
    "message": "Manual ShipStation sync triggered",
    "raw": "2025-01-07T14:32:15 - INFO - [ShipStation] <Nathan|admin> Manual ShipStation sync triggered"
}
```

### 7.3 Multi-line Log Handling

Stack traces and multi-line messages are preserved:
- CSS `white-space: pre-wrap` enables proper display
- Parser appends continuation lines to previous log entry
- Full context maintained for error debugging

---

## 8. Filtering Capabilities

### 8.1 Level Filters

Quick-filter by clicking stat cards or using dropdown:
- ALL (default)
- ERROR
- WARNING
- INFO
- DEBUG

### 8.2 Category Filters

Dropdown options with pattern matching:
- ALL
- API
- Database
- ShipStation
- Auth
- Inventory
- Scheduler
- Email
- Reports

### 8.3 Process Filters

Organized in groups for quick access:

**Reports:**
- EOD Report
- EOW Report
- EOM Report

**Workflows:**
- XML Import
- ShipStation Upload
- ShipStation Sync
- Duplicate Scanner
- Lot Mismatch Scanner

**Operations:**
- Manual Orders
- Email Compose
- ShipStation Deletes

### 8.4 User Filters

- All Users (default)
- System Only
- [Dynamic list of users from current logs]

### 8.5 Time Filters

Hours Back options:
- 1 hour
- 6 hours
- 24 hours (default)
- 48 hours
- 7 days (168 hours)

### 8.6 Line Limits

Options: 100, 250, 500 (default), 1000, 2000

### 8.7 Text Search

- Supports regex patterns
- Falls back to simple string search if regex invalid
- 300ms debounce to reduce API calls

---

## 9. Files Modified

### 9.1 New Files Created

| File | Purpose |
|------|---------|
| `src/utils/server_logger.py` | Core logging module |
| `logs.html` | Admin web interface |
| `logs/` | Directory for log files |

### 9.2 Files Modified

| File | Changes |
|------|---------|
| `app.py` | Added logging API endpoints, user tracking in 8+ endpoints |
| `src/unified_shipstation_sync.py` | Enhanced error logging with context |
| `src/scheduled_duplicate_scanner.py` | Added server logging |
| `src/scheduled_shipstation_upload.py` | Added server logging |
| `src/scheduled_lot_mismatch_scanner.py` | Added server logging |

---

## 10. Lessons Learned

### 10.1 Authentication Import Path

**Problem:** Initial implementation used wrong import path causing user tracking to fail silently.

**Wrong:**
```python
from src.services.auth import get_current_user
user_name = user.get('first_name')  # Dict access
```

**Correct:**
```python
from src.auth.middleware import get_current_user
user_name = user.first_name  # Object attribute access
```

**Key Insight:** The Replit Auth middleware returns an object with attributes, not a dictionary.

### 10.2 Log Format Evolution

**Original format (verbose):**
```
2025-01-07T14:32:15 - INFO - oracare - [ShipStation] message
```

**Final format (streamlined):**
```
2025-01-07T14:32:15 - INFO - [ShipStation] <Nathan|admin> message
```

**Changes:**
- Removed redundant "oracare" logger name prefix
- Added user/role tracking inline
- Cleaner format for easier parsing and display

### 10.3 Browser Cache Issues

**Problem:** CSS and JavaScript changes not visible after deployment.

**Solution:** Instruct users to perform hard refresh (`Ctrl+Shift+R`).

**Future consideration:** Add cache-busting query parameters to static assets.

### 10.4 Multi-line Message Display

**Problem:** Stack traces and long error messages displayed on single line.

**Solution:** 
```css
.log-line {
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: anywhere;
}
```

### 10.5 Dynamic Filter Population

**Learning:** Populate filter dropdowns from actual data rather than hardcoding options.

**Implementation:** `updateUserDropdown(logs)` extracts unique users from current log data and rebuilds the dropdown, preserving user's current selection.

---

## 11. Known Issues & Limitations

### 11.1 Log File Limitations

- Maximum 10MB per file before rotation
- 7 backup files = ~70MB total retention
- Older logs are automatically deleted

### 11.2 Production vs Development

- Development and production have SEPARATE log files
- Production logs are NOT visible from development workspace
- User must manually share production log file contents for troubleshooting

### 11.3 Time Zone Handling

- Server logs in UTC
- Frontend converts to user's local timezone
- Timezone conversion handled in JavaScript `formatTimestamp()` function

### 11.4 LSP Diagnostics

The `server_logger.py` file shows LSP diagnostics related to:
- pytz type hints
- Optional type imports

These are lint warnings, not functional issues.

---

## 12. Future Enhancements

### 12.1 Potential Improvements

1. **Log Aggregation** - Combine logs from multiple sources (workflows)
2. **Alert Thresholds** - Notify on high error rates
3. **Log Export** - Export filtered logs as CSV/JSON
4. **Retention Policies** - Configurable log retention periods
5. **Performance Metrics** - Track request durations, DB query times
6. **User Session Tracking** - Link activities to user sessions

### 12.2 Monitoring Integration

Consider integration with:
- External log aggregation services
- Error tracking platforms (Sentry, Rollbar)
- Metrics dashboards (Grafana, DataDog)

---

## Appendix A: Source Code Reference

### Key Files

1. **Backend Logger:** `src/utils/server_logger.py`
2. **Web Interface:** `logs.html`
3. **Main Application:** `app.py` (logging API endpoints)

### Testing

Manual testing via:
1. Navigate to Server Logs page (admin only)
2. Trigger various actions (reports, syncs)
3. Verify user/role appears correctly
4. Test all filter combinations
5. Verify auto-refresh functionality

---

## Appendix B: Quick Reference

### Adding Logging to New Endpoints

```python
from src.utils.server_logger import get_logger
from src.auth.middleware import get_current_user

server_logger = get_logger()

# Get user context
user_name = "unknown"
user_role = None
try:
    user = get_current_user()
    if user and user.is_authenticated:
        user_name = user.first_name or user.email or "unknown"
        user_role = user.role
except:
    pass

# Log with context
server_logger.info("Action description", source="ModuleName", user=user_name, role=user_role)
```

### Log Level Guidelines

| Level | Use Case |
|-------|----------|
| DEBUG | Detailed diagnostic information |
| INFO | Normal operations, user actions |
| WARNING | Unexpected but handled situations |
| ERROR | Failures requiring attention |
| CRITICAL | System-wide failures |

---

**Document Version:** 1.0  
**Last Updated:** January 7, 2026  
**Author:** Oracare Development Team
