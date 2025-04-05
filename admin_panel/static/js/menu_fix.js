/**
 * Simple fix for sidebar menu problems in admin panel
 * Prevents menu from automatically closing
 */
document.addEventListener('DOMContentLoaded', function() {
    // Select DOM elements
    const sidebar = document.querySelector('.sidebar');
    const toggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
    
    // Function to toggle sidebar
    function toggleSidebar(event) {
        if (event) event.preventDefault();
        
        const isMobile = window.innerWidth < 768;
        
        if (sidebar) {
            sidebar.classList.toggle('toggled');
            document.body.classList.toggle('sidebar-toggled');
            
            // On desktop keep margin for content
            if (!isMobile) {
                const contentWrapper = document.querySelector('#content-wrapper');
                if (contentWrapper) {
                    if (sidebar.classList.contains('toggled')) {
                        contentWrapper.style.marginLeft = '100px';
                    } else {
                        contentWrapper.style.marginLeft = '250px';
                    }
                }
            }
        }
    }
    
    // Add event listeners to toggle buttons
    toggleButtons.forEach(button => {
        if (button) {
            // Remove any existing click handlers
            const newButton = button.cloneNode(true);
            if (button.parentNode) {
                button.parentNode.replaceChild(newButton, button);
            }
            
            // Add our custom handler
            newButton.addEventListener('click', toggleSidebar);
        }
    });
    
    // Keep sidebar open by default (remove toggled class if present)
    if (sidebar && sidebar.classList.contains('toggled')) {
        sidebar.classList.remove('toggled');
        document.body.classList.remove('sidebar-toggled');
    }
    
    // For mobile devices only - close sidebar when clicking a menu item
    if (window.innerWidth < 768) {
        const menuItems = document.querySelectorAll('.sidebar .nav-item .nav-link');
        menuItems.forEach(item => {
            item.addEventListener('click', function() {
                if (window.innerWidth < 768 && sidebar && !sidebar.classList.contains('toggled')) {
                    toggleSidebar();
                }
            });
        });
    }
    
    console.log('Menu fix script loaded successfully');
});
