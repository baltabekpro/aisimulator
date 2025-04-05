/**
 * Admin panel JavaScript helpers
 * Fixes menu toggle issues and adds additional functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // Fix sidebar toggle issues
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('#sidebarToggle');
    const sidebarToggleTop = document.querySelector('#sidebarToggleTop');
    const contentWrapper = document.querySelector('#content-wrapper');
    const body = document.body;
    
    // Function to toggle sidebar
    function toggleSidebar(forceClose = false) {
        if (forceClose) {
            sidebar.classList.add('toggled');
            body.classList.add('sidebar-toggled');
        } else {
            sidebar.classList.toggle('toggled');
            body.classList.toggle('sidebar-toggled');
        }
        
        // Save state to localStorage
        localStorage.setItem('sidebarState', sidebar.classList.contains('toggled') ? 'closed' : 'open');
    }
    
    // Add event listeners to toggle buttons
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    if (sidebarToggleTop) {
        sidebarToggleTop.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    // Restore sidebar state from localStorage
    const savedState = localStorage.getItem('sidebarState');
    if (savedState === 'open' && sidebar.classList.contains('toggled')) {
        sidebar.classList.remove('toggled');
        body.classList.remove('sidebar-toggled');
    } else if (savedState === 'closed' && !sidebar.classList.contains('toggled')) {
        sidebar.classList.add('toggled');
        body.classList.add('sidebar-toggled');
    }
    
    // Add overlay for mobile view
    const overlay = document.createElement('div');
    overlay.id = 'sidebar-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.right = '0';
    overlay.style.bottom = '0';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    overlay.style.zIndex = '998';
    overlay.style.display = 'none';
    document.body.appendChild(overlay);
    
    // Close sidebar when clicking overlay
    overlay.addEventListener('click', function() {
        toggleSidebar(true);
        overlay.style.display = 'none';
    });
    
    // Show/hide overlay based on sidebar state for mobile
    function updateOverlay() {
        if (window.innerWidth < 768 && !sidebar.classList.contains('toggled')) {
            overlay.style.display = 'block';
        } else {
            overlay.style.display = 'none';
        }
    }
    
    // Add event listener for resize
    window.addEventListener('resize', updateOverlay);
    
    // Update overlay on sidebar toggle
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', updateOverlay);
    }
    if (sidebarToggleTop) {
        sidebarToggleTop.addEventListener('click', updateOverlay);
    }
    
    // Update overlay initially
    updateOverlay();
    
    // Auto close alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-important)');
        alerts.forEach(function(alert) {
            alert.style.transition = 'opacity 1s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 1000);
        });
    }, 5000);
    
    console.log('Admin panel JS initialized successfully');
});
