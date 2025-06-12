/**
 * Edit Company Page JavaScript
 * Handles company editing, module management, and form interactions
 */

// Global variables
let companyId = null;
let pendingChanges = {};

/**
 * Initialize the page when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get company ID from data attribute or global variable
    const companyElement = document.querySelector('[data-company-id]');
    if (companyElement) {
        companyId = parseInt(companyElement.getAttribute('data-company-id'));
    }
    
    // Auto-focus on the first input field
    const nameField = document.getElementById('name');
    if (nameField) {
        nameField.focus();
    }
    
    // Initialize form validation
    initializeFormValidation();
});

/**
 * Initialize form validation and change tracking
 */
function initializeFormValidation() {
    const companyForm = document.querySelector('#companyForm');
    if (companyForm) {
        companyForm.addEventListener('input', function(e) {
            // Mark as pending change when form fields change
            const saveBtn = document.querySelector('button[onclick="saveAllChanges()"]');
            if (saveBtn && !saveBtn.classList.contains('btn-warning')) {
                saveBtn.classList.remove('btn-success');
                saveBtn.classList.add('btn-warning');
                saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Save Pending Changes';
            }
        });
    }
}

/**
 * Toggle a specific module on/off
 * @param {string} moduleName - The name of the module to toggle
 * @param {boolean} enabled - Whether the module should be enabled
 */
function toggleModule(moduleName, enabled) {
    const card = document.querySelector(`[data-module="${moduleName}"]`).closest('.module-card');
    
    // Update visual state immediately
    if (enabled) {
        card.classList.remove('border-secondary');
        card.classList.add('border-success');
    } else {
        card.classList.remove('border-success');
        card.classList.add('border-secondary');
    }
    
    // Store change for batch update
    pendingChanges[moduleName] = enabled;
    
    // Show save button as active
    const saveBtn = document.querySelector('button[onclick="saveAllChanges()"]');
    if (saveBtn) {
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.add('btn-warning');
        saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Save Pending Changes';
    }
}

/**
 * Toggle all modules on or off
 * @param {boolean} enableAll - Whether to enable all modules
 */
function toggleAllModules(enableAll) {
    const toggles = document.querySelectorAll('.module-toggle:not(:disabled)');
    toggles.forEach(toggle => {
        if (toggle.checked !== enableAll) {
            toggle.checked = enableAll;
            toggleModule(toggle.dataset.module, enableAll);
        }
    });
}

/**
 * Save all pending changes (company info and modules)
 */
async function saveAllChanges() {
    if (Object.keys(pendingChanges).length === 0) {
        showToast('Info', 'No changes to save', 'info');
        return;
    }
    
    showLoading();
    
    try {
        // Save company info first
        await saveCompanyInfo();
        
        // Save module changes
        const moduleResult = await saveModuleChanges();
        
        hideLoading();
        
        if (moduleResult.success) {
            showToast('Success', 'All changes saved successfully!', 'success');
            pendingChanges = {};
            
            // Reset save button
            resetSaveButton();
            
            // Update monthly cost if provided
            if (moduleResult.monthly_cost !== undefined) {
                updateMonthlyCost(moduleResult.monthly_cost);
            }
        } else {
            showToast('Error', moduleResult.message || 'Error saving changes', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Error', 'Network error occurred', 'error');
        console.error('Save error:', error);
    }
}

/**
 * Save company basic information
 */
async function saveCompanyInfo() {
    const companyForm = document.getElementById('companyForm');
    if (!companyForm) return;
    
    const formData = new FormData(companyForm);
    const companyFormData = {
        name: formData.get('name'),
        email: formData.get('email'),
        phone: formData.get('phone'),
        address: formData.get('address'),
        is_active: document.getElementById('is_active')?.checked || false
    };
    
    const response = await fetch(`/admin/companies/${companyId}/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(companyFormData)
    });
    
    if (!response.ok) {
        throw new Error('Failed to save company info');
    }
    
    return response.json();
}

/**
 * Save module changes
 */
async function saveModuleChanges() {
    const moduleChanges = [];
    const moduleNotes = document.getElementById('moduleNotes')?.value || '';
    
    for (const [moduleName, enabled] of Object.entries(pendingChanges)) {
        moduleChanges.push({
            module_name: moduleName,
            enabled: enabled,
            notes: moduleNotes
        });
    }
    
    const response = await fetch(`/admin/companies/${companyId}/modules/batch-update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            changes: moduleChanges
        })
    });
    
    if (!response.ok) {
        throw new Error('Failed to save module changes');
    }
    
    return response.json();
}

/**
 * Reset the save button to its default state
 */
function resetSaveButton() {
    const saveBtn = document.querySelector('button[onclick="saveAllChanges()"]');
    if (!saveBtn) return;
    
    saveBtn.classList.remove('btn-warning');
    saveBtn.classList.add('btn-success');
    saveBtn.innerHTML = '<i class="fas fa-check me-1"></i>All Saved';
    
    setTimeout(() => {
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.add('btn-outline-success');
        saveBtn.innerHTML = '<i class="fas fa-save me-1"></i>Save All Changes';
    }, 2000);
}

/**
 * Update the monthly cost display
 * @param {number} cost - The new monthly cost
 */
function updateMonthlyCost(cost) {
    const costElement = document.getElementById('monthly-cost');
    if (costElement) {
        costElement.textContent = `R${cost.toFixed(2)}`;
    }
}

/**
 * Show loading modal
 */
function showLoading() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal && typeof bootstrap !== 'undefined') {
        const modal = new bootstrap.Modal(loadingModal);
        modal.show();
    }
}

/**
 * Hide loading modal
 */
function hideLoading() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getInstance(loadingModal);
        if (modal) {
            modal.hide();
        }
    }
}

/**
 * Show toast notification
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {string} type - Toast type (success, error, info)
 */
function showToast(title, message, type) {
    const toast = document.getElementById('notificationToast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    const toastIcon = document.getElementById('toastIcon');
    
    if (!toast || !toastTitle || !toastMessage || !toastIcon) {
        console.warn('Toast elements not found');
        return;
    }
    
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // Set icon based on type
    switch (type) {
        case 'success':
            toastIcon.className = 'fas fa-check-circle text-success me-2';
            break;
        case 'error':
            toastIcon.className = 'fas fa-exclamation-circle text-danger me-2';
            break;
        case 'info':
        default:
            toastIcon.className = 'fas fa-info-circle text-info me-2';
            break;
    }
    
    // Show toast
    if (typeof bootstrap !== 'undefined') {
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

/**
 * Utility function to get CSRF token if needed
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : null;
}

/**
 * Add CSRF token to fetch requests if available
 * @param {object} headers - Existing headers object
 * @returns {object} Headers with CSRF token added
 */
function addCSRFToken(headers = {}) {
    const token = getCSRFToken();
    if (token) {
        headers['X-CSRFToken'] = token;
    }
    return headers;
}