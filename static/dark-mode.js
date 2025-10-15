/**
 * Global Dark Mode Toggle System
 * Automatically handles dark mode across all pages
 */

(function() {
    'use strict';
    
    // Initialize dark mode on page load
    function initDarkMode() {
        const isDark = localStorage.getItem('darkMode') === 'true';
        if (isDark) {
            document.body.classList.add('dark-mode');
        }
        updateToggleButton();
    }
    
    // Toggle dark mode
    function toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDark ? 'true' : 'false');
        updateToggleButton();
    }
    
    // Update the toggle button icon
    function updateToggleButton() {
        const isDark = document.body.classList.contains('dark-mode');
        const toggleBtn = document.querySelector('.dark-mode-toggle');
        if (toggleBtn) {
            toggleBtn.textContent = isDark ? '☀️' : '🌙';
            toggleBtn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        }
    }
    
    // Make toggleDarkMode available globally
    window.toggleDarkMode = toggleDarkMode;
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDarkMode);
    } else {
        initDarkMode();
    }
})();
