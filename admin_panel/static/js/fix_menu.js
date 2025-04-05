/**
 * Ultra simple fix for menu auto-closing issues
 * This script forces the menu to behave correctly by overriding
 * any problematic event handlers
 */
(function() {
  // Wait for DOM to be fully loaded
  document.addEventListener('DOMContentLoaded', function() {
    console.log('Menu fix script is running');
    
    // Get elements
    const sidebar = document.querySelector('.sidebar');
    const toggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
    const body = document.body;
    
    if (!sidebar || toggleButtons.length === 0) {
      console.warn('Could not find sidebar or toggle buttons');
      return;
    }
    
    // Remove any existing click handlers from toggle buttons
    toggleButtons.forEach(function(button) {
      const newButton = button.cloneNode(true);
      button.parentNode.replaceChild(newButton, button);
    });
    
    // Reset sidebar state - ensure it's open by default on desktop
    function resetSidebarState() {
      const isMobile = window.innerWidth < 768;
      
      if (!isMobile) {
        // Keep sidebar open on desktop
        if (sidebar.classList.contains('toggled')) {
          sidebar.classList.remove('toggled');
          body.classList.remove('sidebar-toggled');
        }
      } else {
        // Keep sidebar closed on mobile
        if (!sidebar.classList.contains('toggled')) {
          sidebar.classList.add('toggled');
          body.classList.add('sidebar-toggled');
        }
      }
    }
    
    // Add our own toggle handler
    function addToggleHandler() {
      const newToggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
      
      newToggleButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          sidebar.classList.toggle('toggled');
          body.classList.toggle('sidebar-toggled');
          
          // Save state in localStorage
          localStorage.setItem('sidebarToggled', sidebar.classList.contains('toggled'));
          
          console.log('Sidebar toggled', sidebar.classList.contains('toggled'));
          return false;
        });
      });
    }
    
    // Apply the fix
    function applyFix() {
      // Reset sidebar state on page load
      resetSidebarState();
      
      // Add new toggle handlers
      addToggleHandler();
      
      // IMPORTANT: Force sidebar to stay toggled or not based on user preference
      const savedState = localStorage.getItem('sidebarToggled');
      if (savedState === 'true') {
        sidebar.classList.add('toggled');
        body.classList.add('sidebar-toggled');
      } else if (savedState === 'false' && window.innerWidth >= 768) {
        sidebar.classList.remove('toggled');
        body.classList.remove('sidebar-toggled');
      }
      
      // Update sidebar on window resize
      window.addEventListener('resize', function() {
        const isMobile = window.innerWidth < 768;
        
        if (isMobile) {
          sidebar.classList.add('toggled');
          body.classList.add('sidebar-toggled');
        } else if (localStorage.getItem('sidebarToggled') !== 'true') {
          sidebar.classList.remove('toggled');
          body.classList.remove('sidebar-toggled');
        }
      });
      
      console.log('Menu fix applied successfully!');
    }
    
    // Apply fix immediately
    applyFix();
    
    // For extra reliability, re-apply after a short delay
    setTimeout(applyFix, 500);
  });
})();
