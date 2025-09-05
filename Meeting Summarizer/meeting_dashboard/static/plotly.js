// Custom JavaScript for Meeting Dashboard

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    initializeTooltips();
    initializeAnimations();
});

// Initialize dashboard components
function initializeDashboard() {
    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
                submitBtn.disabled = true;
            }
        });
    });

    // Initialize file upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const fileName = file.name;
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                
                // Show file info
                const fileInfo = document.createElement('div');
                fileInfo.className = 'alert alert-info mt-2';
                fileInfo.innerHTML = `
                    <i class="fas fa-file me-2"></i>
                    <strong>${fileName}</strong> (${fileSize} MB)
                `;
                
                // Remove existing file info
                const existingInfo = this.parentNode.querySelector('.alert');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                this.parentNode.appendChild(fileInfo);
            }
        });
    });
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize animations
function initializeAnimations() {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });

    // Add slide-in animations to list items
    const listItems = document.querySelectorAll('.list-group-item');
    listItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 0.05}s`;
        item.classList.add('slide-in-left');
    });
}

// Utility function to show loading state
function showLoading(element) {
    element.classList.add('loading');
    const originalContent = element.innerHTML;
    element.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    return originalContent;
}

// Utility function to hide loading state
function hideLoading(element, originalContent) {
    element.classList.remove('loading');
    element.innerHTML = originalContent;
}

// Function to update action item status
function updateStatus(actionItemId, status) {
    const statusMap = {
        'completed': 'Completed',
        'in_progress': 'In Progress',
        'pending': 'Pending',
        'cancelled': 'Cancelled'
    };

    fetch(`/api/action_items/${actionItemId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showToast('Status updated successfully!', 'success');
            
            // Reload page after a short delay
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showToast('Error updating status: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating status', 'error');
    });
}

// Function to show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// Function to toggle transcript visibility
function toggleTranscript() {
    const content = document.getElementById('transcriptContent');
    const toggle = document.getElementById('transcriptToggle');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = 'Hide';
        content.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        content.style.display = 'none';
        toggle.textContent = 'Show';
    }
}

// Function to toggle text input in upload form
function toggleTextInput() {
    const textSection = document.getElementById('textInputSection');
    const fileInput = document.getElementById('transcript_file');
    
    if (textSection.style.display === 'none') {
        textSection.style.display = 'block';
        fileInput.disabled = true;
        fileInput.value = '';
        textSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        textSection.style.display = 'none';
        fileInput.disabled = false;
        document.getElementById('transcript_text').value = '';
    }
}

// Function to validate file upload
function validateFileUpload(fileInput) {
    const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const allowedExtensions = ['.txt', '.pdf', '.docx', '.md'];
    const maxSize = 16 * 1024 * 1024; // 16MB
    
    if (fileInput.files.length === 0) {
        return { valid: true }; // No file selected is valid
    }
    
    const file = fileInput.files[0];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
        return { 
            valid: false, 
            message: 'Please select a valid file type (.txt, .pdf, .docx, .md)' 
        };
    }
    
    if (file.size > maxSize) {
        return { 
            valid: false, 
            message: 'File size must be less than 16MB' 
        };
    }
    
    return { valid: true };
}

// Function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard!', 'success');
    }, function(err) {
        console.error('Could not copy text: ', err);
        showToast('Failed to copy to clipboard', 'error');
    });
}

// Function to export data as JSON
function exportAsJSON(data, filename) {
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = filename || 'export.json';
    link.click();
}

// Function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Function to format datetime
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Function to debounce function calls
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Function to throttle function calls
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Initialize search functionality
function initializeSearch() {
    const searchInputs = document.querySelectorAll('[data-search]');
    
    searchInputs.forEach(input => {
        const searchTarget = input.getAttribute('data-search');
        const targetElements = document.querySelectorAll(searchTarget);
        
        const debouncedSearch = debounce(function() {
            const searchTerm = input.value.toLowerCase();
            
            targetElements.forEach(element => {
                const text = element.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    element.style.display = '';
                } else {
                    element.style.display = 'none';
                }
            });
        }, 300);
        
        input.addEventListener('input', debouncedSearch);
    });
}

// Initialize search when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeSearch);

// Export functions for global use
window.updateStatus = updateStatus;
window.toggleTranscript = toggleTranscript;
window.toggleTextInput = toggleTextInput;
window.copyToClipboard = copyToClipboard;
window.exportAsJSON = exportAsJSON;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
