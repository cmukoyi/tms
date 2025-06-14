/**
 * Enhanced Edit Company Page JavaScript
 * Handles company editing, module management, pricing, and form interactions
 */

// Global variables
let companyId = null;
let pendingChanges = {};
let pricingModal = null;

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
    
    // Initialize pricing modal
    const pricingModalElement = document.getElementById('pricingModal');
    if (pricingModalElement) {
        pricingModal = new bootstrap.Modal(pricingModalElement);
    }
    
    // Initialize module toggle listeners
    initializeModuleToggles();
    
    // Initialize pricing listeners
    initializePricingListeners();
    
    // Auto-focus on the first input field
    const nameField = document.getElementById('name');
    if (nameField) {
        nameField.focus();
    }
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize pricing actions visibility
    updatePricingActionsVisibility();
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
 * Initialize pricing-related event listeners
 */
function initializePricingListeners() {
    // Price difference calculator
    const customPriceInput = document.getElementById('pricing_custom_price');
    if (customPriceInput) {
        customPriceInput.addEventListener('input', calculatePriceDifference);
    }
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
        
        companyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveCompanyDetails();
        });
    }
}

/**
 * Toggle a specific module on/off with pricing consideration
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
        
        // Update pricing actions visibility
        const pricingActions = card.querySelector('.pricing-actions');
        if (pricingActions) {
            pricingActions.style.display = enabled ? 'block' : 'none';
        }
    }
    
    // Store change for batch update
    pendingChanges[moduleName] = enabled;
    
    // Update monthly cost calculation
    updateMonthlyCostCalculation();
    
    // Show save button as active
    markPendingChanges();
}

/**
 * Update pricing actions visibility based on module state
 */
function updatePricingActionsVisibility() {
    document.querySelectorAll('.module-card').forEach(card => {
        const toggle = card.querySelector('.module-toggle');
        const pricingActions = card.querySelector('.pricing-actions');
        
        if (toggle && pricingActions) {
            pricingActions.style.display = toggle.checked ? 'block' : 'none';
        }
    });
}

/**
 * Calculate monthly cost based on current module states and custom pricing
 */
function updateMonthlyCostCalculation() {
    let totalCost = 0;
    
    document.querySelectorAll('.module-toggle:checked').forEach(toggle => {
        const card = toggle.closest('.module-card');
        
        // Look for custom pricing first
        const customPricing = card.querySelector('.custom-pricing');
        if (customPricing) {
            const priceMatch = customPricing.textContent.match(/R\s*([\d.,]+)/);
            if (priceMatch) {
                totalCost += parseFloat(priceMatch[1].replace(',', ''));
            }
        } else {
            // Use default pricing
            const defaultPricing = card.querySelector('.default-pricing, .text-success.fw-bold');
            if (defaultPricing && defaultPricing.textContent.includes('R')) {
                const priceMatch = defaultPricing.textContent.match(/R\s*([\d.,]+)/);
                if (priceMatch) {
                    totalCost += parseFloat(priceMatch[1].replace(',', ''));
                }
            }
        }
    });
    
    // Update monthly cost display
    const monthlyCostElement = document.getElementById('monthly-cost');
    if (monthlyCostElement) {
        monthlyCostElement.textContent = `R${totalCost.toFixed(2)}`;
    }
    
    return totalCost;
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
            } else {
                // Recalculate based on current state
                updateMonthlyCostCalculation();
            }
            
            // Update pricing actions visibility
            updatePricingActionsVisibility();
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
 * Save module changes using JSON instead of FormData
 */
async function saveModuleChanges() {
    console.log('Saving module changes...');
    
    // Prepare changes array in the format expected by the Flask route
    const changes = [];
    
    // Get all module toggles and their current states
    document.querySelectorAll('.module-toggle').forEach(toggle => {
        const moduleName = toggle.dataset.module;
        const isEnabled = toggle.checked;
        
        // Only include modules that have actually changed
        if (pendingChanges.hasOwnProperty(moduleName)) {
            changes.push({
                module_name: moduleName,
                enabled: isEnabled,
                notes: isEnabled ? 'Enabled via admin interface' : 'Disabled via admin interface'
            });
        }
    });
    
    console.log('Changes to send:', changes);
    
    if (changes.length === 0) {
        console.log('No changes to save');
        return { success: true, message: 'No changes to save' };
    }
    
    // Prepare JSON data
    const requestData = {
        changes: changes
    };
    
    console.log('Request data:', requestData);
    console.log('Sending to:', `/admin/companies/${companyId}/modules/batch-update`);
    
    // Send JSON request with proper headers
    const response = await fetch(`/admin/companies/${companyId}/modules/batch-update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(requestData)
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        
        try {
            const errorData = JSON.parse(errorText);
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        } catch (parseError) {
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
    }
    
    const result = await response.json();
    console.log('Response data:', result);
    
    return result;
}

/**
 * Save company details
 */
async function saveCompanyDetails() {
    const form = document.getElementById('companyForm');
    if (!form) return;
    
    const formData = new FormData(form);
    
    const data = {
        name: formData.get('name'),
        email: formData.get('email'),
        phone: formData.get('phone') || null,
        address: formData.get('address') || null,
        is_active: formData.has('is_active')
    };
    
    try {
        const response = await fetch(`/admin/companies/${companyId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', 'Company details updated successfully!', 'success');
            return true;
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showToast('Error', 'Error updating company details: ' + error.message, 'error');
        return false;
    }
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
 * @param {string} type - Toast type (success, error, info, warning)
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
    
    // Remove existing classes
    toast.classList.remove('border-success', 'border-danger', 'border-warning', 'border-info');
    
    // Set icon and styling based on type
    switch (type) {
        case 'success':
            toastIcon.className = 'fas fa-check-circle text-success me-2';
            toast.classList.add('border-success');
            break;
        case 'error':
            toastIcon.className = 'fas fa-exclamation-circle text-danger me-2';
            toast.classList.add('border-danger');
            break;
        case 'warning':
            toastIcon.className = 'fas fa-exclamation-triangle text-warning me-2';
            toast.classList.add('border-warning');
            break;
        case 'info':
        default:
            toastIcon.className = 'fas fa-info-circle text-info me-2';
            toast.classList.add('border-info');
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

// ============================================================================
// PRICING FUNCTIONS
// ============================================================================

/**
 * Show pricing modal for a specific module
 * @param {string} moduleId - Module ID
 * @param {string} moduleName - Module display name
 * @param {string} defaultPrice - Default module price
 * @param {string} currentPrice - Current effective price
 */
function showPricingModal(moduleId, moduleName, defaultPrice, currentPrice) {
    if (!pricingModal) {
        console.error('Pricing modal not initialized');
        return;
    }
    
    document.getElementById('pricing_module_id').value = moduleId;
    document.getElementById('pricing_module_name').value = moduleName;
    document.getElementById('pricing_default_price').value = parseFloat(defaultPrice).toFixed(2);
    document.getElementById('pricing_custom_price').value = parseFloat(currentPrice).toFixed(2);
    document.getElementById('pricing_notes').value = '';
    
    calculatePriceDifference();
    pricingModal.show();
}

/**
 * Calculate and display price difference
 */
function calculatePriceDifference() {
    const defaultPrice = parseFloat(document.getElementById('pricing_default_price').value) || 0;
    const customPrice = parseFloat(document.getElementById('pricing_custom_price').value) || 0;
    const difference = customPrice - defaultPrice;
    const diffElement = document.getElementById('price_difference');
    
    if (!diffElement) return;
    
    if (difference > 0) {
        diffElement.innerHTML = `<span class="text-danger"><i class="fas fa-arrow-up"></i> R${difference.toFixed(2)} more than default</span>`;
    } else if (difference < 0) {
        diffElement.innerHTML = `<span class="text-success"><i class="fas fa-arrow-down"></i> R${Math.abs(difference).toFixed(2)} less than default</span>`;
    } else {
        diffElement.innerHTML = `<span class="text-muted">Same as default price</span>`;
    }
}

/**
 * Set custom pricing for a module
 */
function setCustomPricing() {
    const moduleId = document.getElementById('pricing_module_id').value;
    const customPrice = document.getElementById('pricing_custom_price').value;
    const notes = document.getElementById('pricing_notes').value;
    
    if (!customPrice || customPrice < 0) {
        showToast('Error', 'Please enter a valid custom price', 'error');
        return;
    }
    
    // Show loading state
    const setBtn = document.querySelector('button[onclick="setCustomPricing()"]');
    const originalText = setBtn.innerHTML;
    setBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Setting...';
    setBtn.disabled = true;
    
    fetch(`/admin/billing/pricing/${companyId}/set`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            module_id: moduleId,
            custom_price: parseFloat(customPrice),
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Custom pricing set successfully!', 'success');
            pricingModal.hide();
            
            // Update monthly cost display
            if (data.new_total !== undefined) {
                updateMonthlyCost(data.new_total);
            } else {
                updateMonthlyCostCalculation();
            }
            
            // Refresh the page to show updated pricing
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'Error setting custom pricing: ' + error.message, 'error');
    })
    .finally(() => {
        setBtn.innerHTML = originalText;
        setBtn.disabled = false;
    });
}

/**
 * Remove custom pricing for a module
 * @param {string} moduleId - Module ID
 * @param {string} moduleName - Module display name
 */
function removeModuleCustomPricing(moduleId, moduleName) {
    if (!confirm(`Are you sure you want to remove custom pricing for "${moduleName}"?`)) {
        return;
    }
    
    fetch(`/admin/billing/pricing/${companyId}/remove`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            module_id: moduleId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Custom pricing removed successfully!', 'success');
            
            // Update monthly cost display
            if (data.new_total !== undefined) {
                updateMonthlyCost(data.new_total);
            } else {
                updateMonthlyCostCalculation();
            }
            
            // Refresh the page to show updated pricing
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'Error removing custom pricing: ' + error.message, 'error');
    });
}

// ============================================================================
// KEYBOARD SHORTCUTS AND AUTO-SAVE
// ============================================================================

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+S to save
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveAllChanges();
    }
    
    // Escape to discard changes
    if (e.key === 'Escape' && Object.keys(pendingChanges).length > 0) {
        if (confirm('Are you sure you want to discard all unsaved changes?')) {
            location.reload();
        }
    }
});

// Auto-save functionality (optional)
let autoSaveTimeout;
function scheduleAutoSave() {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
        if (Object.keys(pendingChanges).length > 0) {
            console.log('Auto-saving changes...');
            saveAllChanges();
        }
    }, 30000); // Auto-save after 30 seconds of inactivity
}

// Schedule auto-save on any change
document.addEventListener('change', scheduleAutoSave);
document.addEventListener('input', scheduleAutoSave);

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Format currency for display
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-ZA', {
        style: 'currency',
        currency: 'ZAR',
        minimumFractionDigits: 2
    }).format(amount);
}

/**
 * Validate price input
 * @param {string} price - Price string to validate
 * @returns {boolean} Whether the price is valid
 */
function isValidPrice(price) {
    const num = parseFloat(price);
    return !isNaN(num) && num >= 0;
}