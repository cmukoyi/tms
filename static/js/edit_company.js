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
    // Get company ID from data attribute
    const companyElement = document.querySelector('[data-company-id]');
    if (companyElement) {
        companyId = parseInt(companyElement.getAttribute('data-company-id'));
        console.log('Company ID:', companyId);
    }
    
    // Initialize module toggle listeners
    initializeModuleToggles();
    
    // Auto-focus on the first input field
    const nameField = document.getElementById('name');
    if (nameField) {
        nameField.focus();
    }
    
    // Initialize form validation
    initializeFormValidation();
});

/**
 * Initialize module toggle event listeners
 */
function initializeModuleToggles() {
    document.querySelectorAll('.module-toggle').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const moduleName = this.dataset.module;
            const isEnabled = this.checked;
            console.log(`Module ${moduleName} toggled to ${isEnabled}`);
            toggleModule(moduleName, isEnabled);
        });
    });
}

/**
 * Initialize form validation and change tracking
 */
function initializeFormValidation() {
    const companyForm = document.querySelector('#companyForm');
    if (companyForm) {
        companyForm.addEventListener('input', function(e) {
            // Mark as pending change when form fields change
            markPendingChanges();
        });
    }
}

/**
 * Toggle a specific module on/off
 * @param {string} moduleName - The name of the module to toggle
 * @param {boolean} enabled - Whether the module should be enabled
 */
function toggleModule(moduleName, enabled) {
    const toggle = document.querySelector(`[data-module="${moduleName}"]`);
    const card = toggle ? toggle.closest('.module-card') : null;
    
    // Update visual state immediately
    if (card) {
        if (enabled) {
            card.classList.remove('border-secondary');
            card.classList.add('border-success');
        } else {
            card.classList.remove('border-success');
            card.classList.add('border-secondary');
        }
    }
    
    // Store change for batch update
    pendingChanges[moduleName] = enabled;
    
    // Show save button as active
    markPendingChanges();
}

/**
 * Mark that there are pending changes
 */
function markPendingChanges() {
    const saveBtn = document.querySelector('button[onclick="saveAllChanges()"]');
    if (saveBtn && !saveBtn.innerHTML.includes('Pending')) {
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
    console.log('saveAllChanges called');
    console.log('Pending changes:', pendingChanges);
    
    if (!companyId) {
        showToast('Error', 'Company ID not found', 'error');
        return;
    }
    
    // Show loading state
    const saveBtn = document.querySelector('button[onclick="saveAllChanges()"]');
    const originalText = saveBtn.innerHTML;
    
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    saveBtn.disabled = true;
    
    try {
        // Save module changes
        const result = await saveModuleChanges();
        
        if (result.success) {
            showToast('Success', 'Changes saved successfully!', 'success');
            pendingChanges = {};
            
            // Reset save button
            resetSaveButton();
            
            // Update monthly cost if provided
            if (result.monthly_cost !== undefined) {
                updateMonthlyCost(result.monthly_cost);
            }
        } else {
            showToast('Error', result.message || 'Error saving changes', 'error');
        }
    } catch (error) {
        console.error('Save error:', error);
        showToast('Error', 'Network error occurred: ' + error.message, 'error');
    } finally {
        // Reset button state
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    }
}

/**
 * Save module changes using the correct endpoint
 */
async function saveModuleChanges() {
    console.log('Saving module changes...');
    
    // Prepare form data
    const formData = new FormData();
    
    // Add all currently checked modules
    document.querySelectorAll('.module-toggle:checked').forEach(toggle => {
        formData.append('enabled_modules', toggle.dataset.module);
    });
    
    // Add notes if any
    const notes = document.getElementById('moduleNotes')?.value;
    if (notes) {
        formData.append('notes', notes);
    }
    
    console.log('FormData prepared, sending to:', `/admin/companies/${companyId}/modules`);
    
    // const response = await fetch(`/admin/companies/${companyId}/modules`, {

    const response = await fetch(`/admin/companies/${companyId}/modules/batch-update`, {

        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    });
    
    console.log('Response status:', response.status);
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const result = await response.json();
    console.log('Response data:', result);
    
    return result;
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
        saveBtn.classList.add('btn-success');
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
        console.warn('Toast elements not found, using alert fallback');
        alert(`${title}: ${message}`);
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
    } else {
        console.warn('Bootstrap not loaded, using alert fallback');
        alert(`${title}: ${message}`);
    }
}