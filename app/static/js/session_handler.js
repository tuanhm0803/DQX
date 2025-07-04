/**
 * Session handler for DQX application
 * Handles session timeout and authentication checks
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if session is valid
    checkSessionStatus();
    
    // Set up periodic checks every minute
    setInterval(checkSessionStatus, 60000); // Check every minute
});

/**
 * Check if the current session is valid
 * If not, show the login modal
 */
function checkSessionStatus() {
    fetch('/api/auth/session-check', {
        method: 'GET',
        credentials: 'same-origin', // Include cookies
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            // Session is invalid, show login modal
            showLoginModal();
            return { valid: false };
        }
        return response.json();
    })
    .then(data => {
        if (data && !data.valid) {
            showLoginModal();
        }
    })
    .catch(error => {
        console.error('Error checking session status:', error);
    });
}

/**
 * Show the login modal
 */
function showLoginModal() {
    // Get the modal element
    const loginModal = document.getElementById('loginModal');
    
    // If the modal exists, show it
    if (loginModal) {
        const modal = new bootstrap.Modal(loginModal);
        modal.show();
    } else {
        // If the modal doesn't exist (shouldn't happen, but just in case),
        // redirect to the login page
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
    }
}
