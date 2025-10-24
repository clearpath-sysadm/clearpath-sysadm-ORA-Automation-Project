// Timezone utility functions for Oracare Fulfillment Dashboard
// This file provides timezone-aware date formatting across all pages

/**
 * Get the user's timezone - auto-detected from browser
 * @returns {string} The timezone identifier (e.g., 'America/Chicago')
 */
function getUserTimezone() {
    // Auto-detect from browser, fallback to localStorage, then default
    try {
        const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        return localStorage.getItem('userTimezone') || browserTimezone || 'America/New_York';
    } catch (e) {
        return localStorage.getItem('userTimezone') || 'America/New_York';
    }
}

/**
 * Format a date string with timezone awareness
 * @param {string|Date} dateInput - The date to format
 * @param {Object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted date string
 */
function formatDateWithTimezone(dateInput, options = {}) {
    const timezone = getUserTimezone();
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    
    // Default options
    const defaultOptions = {
        timeZone: timezone,
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        ...options
    };
    
    const formatter = new Intl.DateTimeFormat('en-US', defaultOptions);
    return formatter.format(date);
}

/**
 * Format a date for display with timezone conversion (M/D/YYYY)
 * USE THIS FOR: Timestamps/datetimes that should reflect user's timezone
 * DON'T USE FOR: Calendar dates that should stay fixed (use formatChargeReportDate)
 * @param {string|Date} dateInput - The date to format
 * @returns {string} Formatted date string
 */
function formatDate(dateInput) {
    return formatDateWithTimezone(dateInput, {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric'
    });
}

/**
 * Format a datetime with time (M/D/YYYY, H:MM AM/PM)
 * @param {string|Date} dateInput - The datetime to format
 * @returns {string} Formatted datetime string
 */
function formatDateTime(dateInput) {
    return formatDateWithTimezone(dateInput, {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

/**
 * Format a datetime with seconds (M/D/YYYY, H:MM:SS AM/PM)
 * @param {string|Date} dateInput - The datetime to format
 * @returns {string} Formatted datetime string
 */
function formatDateTimeWithSeconds(dateInput) {
    return formatDateWithTimezone(dateInput, {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });
}

/**
 * Format a time only (H:MM AM/PM)
 * @param {string|Date} dateInput - The datetime to format
 * @returns {string} Formatted time string
 */
function formatTime(dateInput) {
    return formatDateWithTimezone(dateInput, {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

/**
 * Get relative time string (e.g., "2 minutes ago")
 * @param {string|Date} dateInput - The date to compare
 * @returns {string} Relative time string
 */
function getRelativeTime(dateInput) {
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return formatDate(date);
}

/**
 * Convert a date string to ISO format with timezone offset
 * Useful for API calls that need timezone information
 * @param {string|Date} dateInput - The date to convert
 * @returns {string} ISO string with timezone
 */
function toISOWithTimezone(dateInput) {
    const timezone = getUserTimezone();
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    
    // Get the offset for the timezone
    const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    
    return formatter.format(date);
}

/**
 * Format date for display in charge report (date-only, no timezone conversion)
 * Use this for calendar dates that should NOT shift based on timezone
 * @param {string} dateStr - Date string from API (YYYY-MM-DD)
 * @returns {string} Formatted date (M/D/YYYY)
 */
function formatChargeReportDate(dateStr) {
    // For date-only fields, parse and format WITHOUT timezone conversion
    // This ensures Sept 30 stays Sept 30 regardless of user's timezone
    const parts = dateStr.split('-');
    const year = parts[0];
    const month = parseInt(parts[1], 10);
    const day = parseInt(parts[2], 10);
    
    return `${month}/${day}/${year}`;
}

/**
 * Get current date/time in user's timezone
 * @returns {Date} Current date in user's timezone
 */
function getCurrentDateInTimezone() {
    const timezone = getUserTimezone();
    const now = new Date();
    
    // This returns the current date, but formatted methods will use the user's timezone
    return now;
}

/**
 * Show timezone indicator on page (optional)
 * Call this to display current timezone setting to users
 */
function showTimezoneIndicator() {
    const timezone = getUserTimezone();
    const tzNames = {
        'America/New_York': 'ET',
        'America/Chicago': 'CT',
        'America/Denver': 'MT',
        'America/Phoenix': 'MST',
        'America/Los_Angeles': 'PT',
        'America/Anchorage': 'AKT',
        'Pacific/Honolulu': 'HST',
        'UTC': 'UTC',
        'Europe/London': 'GMT/BST',
        'Europe/Paris': 'CET/CEST',
        'Asia/Dubai': 'GST',
        'Asia/Kolkata': 'IST',
        'Asia/Singapore': 'SGT',
        'Asia/Tokyo': 'JST',
        'Australia/Sydney': 'AEDT/AEST'
    };
    
    return tzNames[timezone] || timezone;
}

/**
 * Format workflow timestamp (for Last Updated field)
 * Returns format like "Oct 23, 7:48 AM" in user's timezone
 * @param {string|Date|null} dateInput - The datetime to format (ISO string or Date object)
 * @returns {string} Formatted datetime string or "Never"
 */
function formatWorkflowTimestamp(dateInput) {
    if (!dateInput || dateInput === null) {
        return 'Never';
    }
    
    const timezone = getUserTimezone();
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    
    if (isNaN(date.getTime())) {
        return 'Invalid Date';
    }
    
    const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
    
    return formatter.format(date);
}
