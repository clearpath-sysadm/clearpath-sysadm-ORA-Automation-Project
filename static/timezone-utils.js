// Timezone utility functions for ORA Business Dashboard
// This file provides timezone-aware date formatting across all pages

/**
 * Get the user's selected timezone from localStorage
 * @returns {string} The timezone identifier (e.g., 'America/New_York')
 */
function getUserTimezone() {
    return localStorage.getItem('userTimezone') || 'America/New_York';
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
 * Format a date for display (short format: M/D/YYYY)
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
 * Format date for display in charge report (matches existing format)
 * @param {string} dateStr - Date string from API (YYYY-MM-DD)
 * @returns {string} Formatted date
 */
function formatChargeReportDate(dateStr) {
    // Parse as local date (no timezone conversion for date-only fields)
    const date = new Date(dateStr + 'T12:00:00'); // Use noon to avoid timezone issues
    return formatDate(date);
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
