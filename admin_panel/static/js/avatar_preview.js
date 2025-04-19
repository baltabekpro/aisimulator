/**
 * Avatar preview functionality for the admin panel
 * Handles both preview before upload and fixing MinIO URLs
 */
document.addEventListener('DOMContentLoaded', function() {
    // Function to convert internal MinIO URLs to externally accessible ones
    function convertMinioUrl(url) {
        if (!url) return url;
        return url.replace('http://minio:9000', 'http://localhost:9000');
    }
    
    // Fix existing image URLs in the page
    document.querySelectorAll('img[src*="minio:9000"]').forEach(img => {
        img.src = convertMinioUrl(img.src);
    });
    
    // Fix image URLs in the table cells (character list)
    document.querySelectorAll('td[data-avatar-url]').forEach(cell => {
        const url = cell.getAttribute('data-avatar-url');
        if (url && url.includes('minio:9000')) {
            const convertedUrl = convertMinioUrl(url);
            cell.setAttribute('data-avatar-url', convertedUrl);
            
            // If there's an img child, update its src too
            const img = cell.querySelector('img');
            if (img) {
                img.src = convertedUrl;
            }
        }
    });
    
    // Add preview functionality to file inputs
    document.querySelectorAll('input[type="file"][accept*="image"]').forEach(input => {
        // Create preview container
        const previewContainer = document.createElement('div');
        previewContainer.className = 'mt-3 mb-3 avatar-preview-container';
        input.parentNode.insertBefore(previewContainer, input.nextSibling);
        
        // Add change event listener
        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    previewContainer.innerHTML = `
                        <div class="card" style="max-width: 200px;">
                            <div class="card-header">Preview</div>
                            <div class="card-body p-0">
                                <img src="${e.target.result}" class="img-fluid" alt="Avatar Preview">
                            </div>
                        </div>
                    `;
                }
                
                reader.readAsDataURL(file);
            } else {
                previewContainer.innerHTML = '';
            }
        });
    });
    
    // Add a helper function to the global scope for dynamic avatar loading
    window.loadAvatarPreview = function(inputElement, previewElementId) {
        const previewElement = document.getElementById(previewElementId);
        if (inputElement.files && inputElement.files[0] && previewElement) {
            const file = inputElement.files[0];
            const reader = new FileReader();
            
            reader.onload = function(e) {
                previewElement.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded" alt="Preview">`;
            }
            
            reader.readAsDataURL(file);
        }
    };
    
    // Fix hidden MinIO URLs in form fields
    document.querySelectorAll('input[type="hidden"][name*="avatar"]').forEach(input => {
        if (input.value && input.value.includes('minio:9000')) {
            input.value = convertMinioUrl(input.value);
        }
    });
    
    // Handle form submission - make sure any MinIO URLs are properly converted
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            // Find all inputs that might contain MinIO URLs
            this.querySelectorAll('input[name*="avatar_url"], input[name*="image_url"], input[name*="avatar"]').forEach(input => {
                if (input.value && input.value.includes('minio:9000')) {
                    input.value = convertMinioUrl(input.value);
                }
            });
        });
    });
    
    console.log("Avatar preview functionality initialized");
});
