// Municipal Tender Opportunity Engine JavaScript

class MunicipalTenderEngine {
    constructor() {
        this.tenders = [];
        this.filteredTenders = [];
        this.currentPage = 1;
        this.itemsPerPage = 12;
        this.currentFilters = {};
        this.companyData = {};
        this.init();
    }

    init() {
        // Get initial data from server
        if (window.municipalTenderData) {
            this.companyData = window.municipalTenderData;
        }
        
        this.loadTenders();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.animateStats();
    }

    async loadTenders() {
        try {
            this.showLoading(true);
            
            // Load from server or use initial data
            if (this.companyData.initialTenders && this.companyData.initialTenders.length > 0) {
                this.tenders = this.companyData.initialTenders;
            } else {
                const response = await fetch('/api/municipal-tenders');
                const data = await response.json();
                
                if (data.success) {
                    this.tenders = data.tenders;
                } else {
                    // Fallback to mock data
                    this.tenders = this.getMockTenders();
                }
            }
            
            this.filteredTenders = [...this.tenders];
            this.displayTenders();
            this.updatePagination();
            
        } catch (error) {
            console.error('Error loading tenders:', error);
            // Use mock data as fallback
            this.tenders = this.getMockTenders();
            this.filteredTenders = [...this.tenders];
            this.displayTenders();
        } finally {
            this.showLoading(false);
        }
    }

    getMockTenders() {
        return [
            {
                id: 1,
                municipality: "City of Cape Town",
                province: "western-cape",
                title: "Supply and Installation of Municipal WiFi Infrastructure",
                category: "it-services",
                description: "Installation of high-speed WiFi networks across 15 municipal buildings and public spaces including Civic Centre, libraries, and community halls.",
                value: 45000000,
                valueDisplay: "R45,000,000",
                closingDate: "2024-07-15",
                daysLeft: 12,
                status: "new",
                requirements: ["CIDB Grade 7+", "ICT Experience", "B-BBEE Level 1-4"],
                matchScore: 94,
                tenderNumber: "CT/2024/IT/045",
                publishedDate: "2024-06-15",
                contactPerson: "Ms. Sarah Johnson",
                contactEmail: "tenders@capetown.gov.za",
                estimatedDuration: "12 months"
            },
            {
                id: 2,
                municipality: "Ekurhuleni Metropolitan Municipality",
                province: "gauteng",
                title: "Construction of Community Sports Complex",
                category: "construction",
                description: "Design and construction of multi-purpose sports complex including soccer field, netball courts, swimming pool, and community centre in Germiston.",
                value: 125000000,
                valueDisplay: "R125,000,000",
                closingDate: "2024-07-08",
                daysLeft: 5,
                status: "closing",
            {
                id: 2,
                municipality: "Ekurhuleni Metropolitan Municipality",
                province: "gauteng",
                title: "Construction of Community Sports Complex",
                category: "construction",
                description: "Design and construction of multi-purpose sports complex including soccer field, netball courts, swimming pool, and community centre in Germiston.",
                value: 125000000,
                valueDisplay: "R125,000,000",
                closingDate: "2024-07-08",
                daysLeft: 5,
                status: "closing",
                requirements: ["CIDB Grade 9", "Construction Experience", "Local Content 70%"],
                matchScore: 87,
                tenderNumber: "EKU/2024/CON/078",
                publishedDate: "2024-05-20",
                contactPerson: "Mr. David Mthembu",
                contactEmail: "procurement@ekurhuleni.gov.za",
                estimatedDuration: "18 months"
            },
            {
                id: 3,
                municipality: "Sol Plaatje Local Municipality",
                province: "northern-cape",
                title: "Waste Management and Recycling Services",
                category: "cleaning",
                description: "Comprehensive waste collection, sorting, and recycling services for residential and commercial areas including weekly collections and recycling plant operation.",
                value: 18500000,
                valueDisplay: "R18,500,000",
                closingDate: "2024-07-03",
                daysLeft: 1,
                status: "urgent",
                requirements: ["Waste Management License", "Fleet of 25+ Vehicles", "B-BBEE Level 1-3"],
                matchScore: 76,
                tenderNumber: "SP/2024/WM/023",
                publishedDate: "2024-06-01",
                contactPerson: "Ms. Nomsa Khumalo",
                contactEmail: "tenders@solplaatje.org.za",
                estimatedDuration: "36 months"
            },
            {
                id: 4,
                municipality: "eThekwini Metropolitan Municipality",
                province: "kwazulu-natal",
                title: "Municipal Financial Management System Upgrade",
                category: "it-services",
                description: "Implementation and customization of integrated financial management system including modules for budgeting, accounting, procurement, and reporting.",
                value: 67200000,
                valueDisplay: "R67,200,000",
                closingDate: "2024-07-22",
                daysLeft: 19,
                status: "new",
                requirements: ["Software Development", "Municipal Finance Experience", "24/7 Support"],
                matchScore: 91,
                tenderNumber: "ETH/2024/IT/156",
                publishedDate: "2024-06-18",
                contactPerson: "Mr. Sipho Ndlovu",
                contactEmail: "itsupport@durban.gov.za",
                estimatedDuration: "24 months"
            },
            {
                id: 5,
                municipality: "Stellenbosch Local Municipality",
                province: "western-cape",
                title: "Strategic Development Plan Consulting Services",
                category: "consulting",
                description: "Development of 5-year Integrated Development Plan including economic development strategy, spatial planning, and community engagement processes.",
                value: 8750000,
                valueDisplay: "R8,750,000",
                closingDate: "2024-07-18",
                daysLeft: 15,
                status: "new",
                requirements: ["Urban Planning Qualification", "IDP Experience", "Community Engagement"],
                matchScore: 83,
                tenderNumber: "STELL/2024/CON/012",
                publishedDate: "2024-06-10",
                contactPerson: "Dr. Maria van der Merwe",
                contactEmail: "planning@stellenbosch.gov.za",
                estimatedDuration: "12 months"
            },
            {
                id: 6,
                municipality: "Buffalo City Metropolitan Municipality",
                province: "eastern-cape",
                title: "LED Street Lighting Upgrade Project",
                category: "construction",
                description: "Replacement of conventional street lighting with energy-efficient LED systems across 1,200 streets including smart controls and maintenance contract.",
                value: 95000000,
                valueDisplay: "R95,000,000",
                closingDate: "2024-07-25",
                daysLeft: 22,
                status: "new",
                requirements: ["Electrical Installation License", "LED Experience", "5-Year Warranty"],
                matchScore: 89,
                tenderNumber: "BC/2024/ELEC/089",
                publishedDate: "2024-06-20",
                contactPerson: "Eng. Thabo Molefe",
                contactEmail: "infrastructure@buffalocity.gov.za",
                estimatedDuration: "15 months"
            }
        ];
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('tenderSearch');
        if (searchInput) {
            searchInput.addEventListener('input', debounce(() => {
                this.applyFilters();
            }, 300));
        }

        // Filter selects
        ['provinceFilter', 'categoryFilter', 'valueFilter'].forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', () => {
                    this.applyFilters();
                });
            }
        });

        // Quick filter chips
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                const filter = e.target.dataset.filter;
                this.toggleQuickFilter(filter);
            });
        });
    }

    applyFilters() {
        const search = document.getElementById('tenderSearch')?.value.toLowerCase() || '';
        const province = document.getElementById('provinceFilter')?.value || '';
        const category = document.getElementById('categoryFilter')?.value || '';
        const valueRange = document.getElementById('valueFilter')?.value || '';

        this.filteredTenders = this.tenders.filter(tender => {
            // Search filter
            const matchesSearch = !search || 
                tender.title.toLowerCase().includes(search) ||
                tender.municipality.toLowerCase().includes(search) ||
                tender.description.toLowerCase().includes(search) ||
                tender.tenderNumber.toLowerCase().includes(search);
            
            // Province filter
            const matchesProvince = !province || tender.province === province;
            
            // Category filter
            const matchesCategory = !category || tender.category === category;
            
            // Value filter
            let matchesValue = true;
            if (valueRange) {
                const value = tender.value;
                switch (valueRange) {
                    case '0-1m':
                        matchesValue = value <= 1000000;
                        break;
                    case '1m-10m':
                        matchesValue = value > 1000000 && value <= 10000000;
                        break;
                    case '10m-50m':
                        matchesValue = value > 10000000 && value <= 50000000;
                        break;
                    case '50m+':
                        matchesValue = value > 50000000;
                        break;
                }
            }
            
            return matchesSearch && matchesProvince && matchesCategory && matchesValue;
        });

        this.currentPage = 1;
        this.displayTenders();
        this.updatePagination();
    }

    toggleQuickFilter(filter) {
        // Remove active class from all chips
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.classList.remove('active');
        });

        // Add active class to clicked chip
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');

        // Apply filter
        switch (filter) {
            case 'urgent':
                this.filteredTenders = this.tenders.filter(t => t.daysLeft <= 2);
                break;
            case 'new':
                this.filteredTenders = this.tenders.filter(t => t.status === 'new');
                break;
            case 'high-match':
                this.filteredTenders = this.tenders.filter(t => t.matchScore >= 90);
                break;
            case 'high-value':
                this.filteredTenders = this.tenders.filter(t => t.value >= 50000000);
                break;
            default:
                this.filteredTenders = [...this.tenders];
        }

        this.currentPage = 1;
        this.displayTenders();
        this.updatePagination();
    }

    displayTenders() {
        const grid = document.getElementById('tenderGrid');
        if (!grid) return;

        // Calculate pagination
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const tendersToShow = this.filteredTenders.slice(startIndex, endIndex);

        if (tendersToShow.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-search" style="font-size: 3rem; margin-bottom: 20px; opacity: 0.5;"></i>
                    <h3>No tenders found</h3>
                    <p>Try adjusting your search filters or check back later for new opportunities.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = tendersToShow.map(tender => `
            <div class="tender-card" data-tender-id="${tender.id}">
                <div class="tender-header">
                    <div class="municipality-name">${tender.municipality}</div>
                    <div class="tender-status status-${tender.status}">
                        ${tender.status.toUpperCase()}
                    </div>
                </div>
                
                <div class="tender-title">${tender.title}</div>
                
                <div class="tender-details">
                    <div class="detail-row">
                        <span class="detail-label">Tender No:</span>
                        <span class="detail-value">${tender.tenderNumber}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Value:</span>
                        <span class="detail-value">${tender.valueDisplay}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Closing Date:</span>
                        <span class="detail-value">${tender.closingDate} (${tender.daysLeft} days)</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Category:</span>
                        <span class="detail-value">${this.formatCategory(tender.category)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Duration:</span>
                        <span class="detail-value">${tender.estimatedDuration}</span>
                    </div>
                </div>
                
                <div class="tender-description">
                    ${tender.description}
                </div>
                
                <div class="match-score">
                    <span class="match-percentage">${tender.matchScore}%</span>
                    <div class="match-label">Match Score</div>
                </div>
                
                <div class="tender-actions">
                    <button class="btn-primary" onclick="showInterestModal(${tender.id})">
                        <i class="fas fa-hand-paper"></i> Express Interest
                    </button>
                    <button class="btn-secondary" onclick="viewTenderDetails(${tender.id})">
                        <i class="fas fa-info-circle"></i> View Details
                    </button>
                </div>
            </div>
        `).join('');
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredTenders.length / this.itemsPerPage);
        const paginationDiv = document.getElementById('pagination');
        const pageInfo = document.getElementById('pageInfo');
        
        if (totalPages <= 1) {
            if (paginationDiv) paginationDiv.style.display = 'none';
            return;
        }

        if (paginationDiv) paginationDiv.style.display = 'flex';
        if (pageInfo) pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;

        // Update button states
        const prevBtn = paginationDiv?.querySelector('.page-btn:first-child');
        const nextBtn = paginationDiv?.querySelector('.page-btn:last-child');
        
        if (prevBtn) prevBtn.disabled = this.currentPage === 1;
        if (nextBtn) nextBtn.disabled = this.currentPage === totalPages;
    }

    changePage(direction) {
        const totalPages = Math.ceil(this.filteredTenders.length / this.itemsPerPage);
        
        this.currentPage += direction;
        if (this.currentPage < 1) this.currentPage = 1;
        if (this.currentPage > totalPages) this.currentPage = totalPages;
        
        this.displayTenders();
        this.updatePagination();
        
        // Scroll to top of tender grid
        document.getElementById('tenderGrid')?.scrollIntoView({ behavior: 'smooth' });
    }

    formatCategory(category) {
        return category.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    showLoading(show) {
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = show ? 'block' : 'none';
        }
    }

    startRealTimeUpdates() {
        // Update stats every 30 seconds
        setInterval(() => {
            this.updateStats();
        }, 30000);
    }

    updateStats() {
        const stats = {
            activeTenders: Math.floor(Math.random() * 50) + 1200,
            newToday: Math.floor(Math.random() * 10) + 15,
            totalValue: Math.floor(Math.random() * 200) + 800,
            matchedTenders: Math.floor(Math.random() * 20) + 140
        };

        Object.keys(stats).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (key === 'totalValue') {
                    element.textContent = `R${stats[key]}M`;
                } else {
                    element.textContent = stats[key];
                }
                
                // Add animation
                element.style.transform = 'scale(1.1)';
                element.style.color = '#00ff00';
                setTimeout(() => {
                    element.style.transform = 'scale(1)';
                    element.style.color = '';
                }, 300);
            }
        });
    }

    animateStats() {
        const statNumbers = document.querySelectorAll('.stat-number');
        statNumbers.forEach((stat, index) => {
            setTimeout(() => {
                stat.style.animation = 'pulse 0.5s ease';
                setTimeout(() => {
                    stat.style.animation = '';
                }, 500);
            }, index * 100);
        });
    }

    async expressInterest(tenderId, formData) {
        try {
            const response = await fetch('/api/municipal-tenders/express-interest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tender_id: tenderId,
                    ...formData
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Interest submitted successfully! You will receive updates on this tender.', 'success');
                this.closeModal();
                
                // Track the event
                this.trackEvent('tender_interest_expressed', { tender_id: tenderId });
            } else {
                this.showNotification(result.error || 'Failed to submit interest. Please try again.', 'error');
            }
            
        } catch (error) {
            console.error('Error expressing interest:', error);
            this.showNotification('Network error. Please check your connection and try again.', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        const messageElement = document.getElementById('notificationMessage');
        
        if (notification && messageElement) {
            messageElement.textContent = message;
            notification.className = `notification ${type}`;
            notification.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.hideNotification();
            }, 5000);
        }
    }

    hideNotification() {
        const notification = document.getElementById('notification');
        if (notification) {
            notification.style.display = 'none';
        }
    }

    closeModal() {
        const modal = document.getElementById('interestModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    trackEvent(eventName, data = {}) {
        // Analytics tracking
        fetch('/api/analytics/track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                event: eventName, 
                data: {
                    ...data,
                    timestamp: new Date().toISOString(),
                    page: 'municipal_tender_engine'
                }
            })
        }).catch(console.error);
    }
}

// Global functions for button interactions
function showInterestModal(tenderId) {
    const tender = engine.tenders.find(t => t.id === tenderId);
    if (!tender) return;

    const modal = document.getElementById('interestModal');
    const modalTenderInfo = document.getElementById('modalTenderInfo');
    const modalTenderId = document.getElementById('modalTenderId');

    if (modalTenderInfo) {
        modalTenderInfo.innerHTML = `
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 10px 0; color: #1a237e;">${tender.title}</h4>
                <p style="margin: 0; color: #666;"><strong>Municipality:</strong> ${tender.municipality}</p>
                <p style="margin: 5px 0 0 0; color: #666;"><strong>Value:</strong> ${tender.valueDisplay}</p>
                <p style="margin: 5px 0 0 0; color: #666;"><strong>Closing Date:</strong> ${tender.closingDate}</p>
            </div>
        `;
    }

    if (modalTenderId) {
        modalTenderId.value = tenderId;
    }

    if (modal) {
        modal.style.display = 'flex';
    }

    // Track modal view
    engine.trackEvent('tender_modal_viewed', { tender_id: tenderId });
}

function submitInterest() {
    const formData = {
        contact_person: document.getElementById('contactPerson')?.value,
        contact_email: document.getElementById('contactEmail')?.value,
        contact_phone: document.getElementById('contactPhone')?.value,
        message: document.getElementById('interestMessage')?.value
    };

    const tenderId = document.getElementById('modalTenderId')?.value;

    // Validate required fields
    if (!formData.contact_person || !formData.contact_email || !formData.contact_phone) {
        engine.showNotification('Please fill in all required fields.', 'error');
        return;
    }

    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.contact_email)) {
        engine.showNotification('Please enter a valid email address.', 'error');
        return;
    }

    engine.expressInterest(parseInt(tenderId), formData);
}

function viewTenderDetails(tenderId) {
    const tender = engine.tenders.find(t => t.id === tenderId);
    if (!tender) return;

    // Track view details
    engine.trackEvent('tender_details_viewed', { tender_id: tenderId });

    // For now, show alert with details (in real app, navigate to detailed page)
    const details = `
📋 TENDER DETAILS

${tender.title}

🏛️ Municipality: ${tender.municipality}
💰 Value: ${tender.valueDisplay}
📅 Closing Date: ${tender.closingDate} (${tender.daysLeft} days remaining)
📋 Tender No: ${tender.tenderNumber}
⏱️ Duration: ${tender.estimatedDuration}

📋 Requirements:
${tender.requirements.map(req => `• ${req}`).join('\n')}

📞 Contact Person: ${tender.contactPerson}
📧 Email: ${tender.contactEmail}

📄 Full documentation available for download.
    `;

    alert(details);
}

function searchTenders() {
    engine.applyFilters();
    engine.trackEvent('tender_search_performed', {
        search_term: document.getElementById('tenderSearch')?.value,
        province: document.getElementById('provinceFilter')?.value,
        category: document.getElementById('categoryFilter')?.value,
        value_range: document.getElementById('valueFilter')?.value
    });
}

function changePage(direction) {
    engine.changePage(direction);
}

function closeModal() {
    engine.closeModal();
}

function hideNotification() {
    engine.hideNotification();
}

function filterByStatus(status) {
    engine.toggleQuickFilter(status);
    engine.trackEvent('quick_filter_used', { filter: status });
}

// Utility function for debouncing
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

// Initialize the application
let engine;
document.addEventListener('DOMContentLoaded', function() {
    engine = new MunicipalTenderEngine();
    
    // Setup keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // ESC to close modal
        if (e.key === 'Escape') {
            closeModal();
        }
        
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('tenderSearch')?.focus();
        }
    });
});