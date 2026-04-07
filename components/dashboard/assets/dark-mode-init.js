/**
 * Dark Mode Initialization
 * Applies saved dark mode preference on page load before rendering
 */

(function() {
    // Check localStorage for saved dark mode preference
    const savedDarkMode = localStorage.getItem('darkMode');
    
    // Apply dark mode immediately if it was previously enabled
    if (savedDarkMode === 'true') {
        document.body.classList.add('dark-mode');
    }
    
    // Listen for storage events from other tabs/windows
    window.addEventListener('storage', function(e) {
        if (e.key === 'darkMode') {
            if (e.newValue === 'true') {
                document.body.classList.add('dark-mode');
            } else {
                document.body.classList.remove('dark-mode');
            }
        }
    });
})();

