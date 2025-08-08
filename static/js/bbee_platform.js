// B-BBEE Platform JavaScript

class BBEEPlatform {
    constructor() {
        this.currentSection = 'calculator';
        this.partnerData = [];
        this.init();
    }

    init() {
        this.animateStats();
        this.loadPartnerData();
        this.setupEventListeners();
        this.showSection('calculator');
    }

    // Animation for statistics on page load
    animateStats() {
        const statNumbers = document.querySelectorAll('.stat-number');
        statNumbers.forEach((stat, index) => {
            const finalValue = stat.textContent;
            stat.textContent = '0';
            
            setTimeout(() => {
                this.animateNumber(stat, finalValue);
            }, index * 200);
        });
    }

    animateNumber(element, finalValue) {
        const duration = 2000;
        const startTime = Date.now();
        const isRand = finalValue.includes('R');
        const isPercentage = finalValue.includes('%');
        const isK = finalValue.includes('K');
        const isT = finalValue.includes('T');
        const isB = finalValue.includes('B');
        
        let numericValue = parseFloat(finalValue.replace(/[R%KTB+]/g, ''));
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = this.easeOutCubic(progress);
            const current = Math.floor(numericValue * eased);
            
            let displayValue = current.toString();
            if (isRand) displayValue = 'R' + displayValue;
            if (isK) displayValue += 'K';
            if (isT) displayValue += 'T';
            if (isB) displayValue += 'B';
            if (isPercentage) displayValue += '%';
            if (finalValue.includes('+')) displayValue += '+';
            
            element.textContent = displayValue;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.textContent = finalValue;
            }
        };
        
        requestAnimationFrame(animate);
    }

    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    setupEventListeners() {
        // Calculator inputs
        const inputs = document.querySelectorAll('#calculatorSection input, #calculatorSection select');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.autoCalculate();
            });
        });

        // Partner search
        const searchInput = document.getElementById('partnerSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchPartners(e.target.value);
            });
        }
    }

    // Show/hide sections
    showSection(sectionName) {
        const sections = ['calculator', 'partnership', 'integration', 'tracker'];
        sections.forEach(section => {
            const element = document.getElementById(section + 'Section');
            if (element) {
                element.style.display = section === sectionName ? 'block' : 'none';
            }
        });
        this.currentSection = sectionName;
    }

    // Auto-calculate when inputs change
    autoCalculate() {
        const blackOwnership = this.getInputValue('blackOwnership');
        const blackManagement = this.getInputValue('blackManagement');
        const blackWomenOwnership = this.getInputValue('blackWomenOwnership');
        
        if (blackOwnership > 0 || blackManagement > 0 || blackWomenOwnership > 0) {
            setTimeout(() => this.calculateBBEE(), 500);
        }
    }

    getInputValue(id) {
        const element = document.getElementById(id);
        return element ? parseInt(element.value) || 0 : 0;
    }

    // B-BBEE Calculator
    calculateBBEE() {
        const data = this.gatherCalculatorData();
        const score = this.computeBBEEScore(data);
        const level = this.getBBEELevel(score);
        const suggestions = this.generateSuggestions(data, score);
        
        this.displayResults(score, level, suggestions);
        
        // Send to backend
        this.saveBBEECalculation(data, score, level);
    }

    gatherCalculatorData() {
        return {
            companySize: document.getElementById('companySize')?.value || '',
            sector: document.getElementById('sector')?.value || '',
            turnover: this.getInputValue('turnover'),
            blackOwnership: this.getInputValue('blackOwnership'),
            blackManagement: this.getInputValue('blackManagement'),
            blackWomenOwnership: this.getInputValue('blackWomenOwnership')
        };
    }

    computeBBEEScore(data) {
        let score = 0;
        
        // Ownership (25 points maximum)
        if (data.blackOwnership >= 51) {
            score += 25;
        } else if (data.blackOwnership >= 25) {
            score += 20;
        } else {
            score += Math.floor(data.blackOwnership * 0.5);
        }
        
        // Management Control (15 points maximum)
        if (data.blackManagement >= 50) {
            score += 15;
        } else if (data.blackManagement >= 25) {
            score += 12;
        } else {
            score += Math.floor(data.blackManagement * 0.3);
        }
        
        // Black Women Ownership Bonus (5 points maximum)
        if (data.blackWomenOwnership >= 25) {
            score += 5;
        } else if (data.blackWomenOwnership >= 10) {
            score += 3;
        } else {
            score += Math.floor(data.blackWomenOwnership * 0.2);
        }
        
        // Simulate other elements (Skills Dev, Enterprise Dev, etc.)
        // In real implementation, these would be separate inputs
        const simulatedOtherElements = Math.floor(Math.random() * 35) + 20;
        score += simulatedOtherElements;
        
        return Math.min(score, 110); // Cap at 110 for Level 1
    }

    getBBEELevel(score) {
        if (score >= 100) return { level: 1, text: "Level 1" };
        if (score >= 95) return { level: 2, text: "Level 2" };
        if (score >= 90) return { level: 3, text: "Level 3" };
        if (score >= 80) return { level: 4, text: "Level 4" };
        if (score >= 75) return { level: 5, text: "Level 5" };
        if (score >= 70) return { level: 6, text: "Level 6" };
        if (score >= 55) return { level: 7, text: "Level 7" };
        return { level: 8, text: "Level 8" };
    }

    generateSuggestions(data, score) {
        const suggestions = [];
        
        if (data.blackOwnership < 51) {
            suggestions.push("💡 Increase black ownership to 51% to maximize ownership points");
        }
        
        if (data.blackManagement < 50) {
            suggestions.push("👥 Improve black representation in management positions");
        }
        
        if (data.blackWomenOwnership < 25) {
            suggestions.push("🚺 Consider increasing black women ownership for bonus points");
        }
        
        if (score < 100) {
            suggestions.push("📈 Focus on skills development and enterprise development programs");
        }
        
        return suggestions;
    }

    displayResults(score, level, suggestions) {
        const resultDiv = document.getElementById('bbeeResult');
        const scoreNumber = document.getElementById('scoreNumber');
        const scoreLevel = document.getElementById('scoreLevel');
        const suggestionsDiv = document.getElementById('suggestions');
        
        if (resultDiv && scoreNumber && scoreLevel) {
            scoreNumber.textContent = score;
            scoreLevel.textContent = level.text + " B-BBEE Contributor";
            
            // Add suggestions
            if (suggestionsDiv && suggestions.length > 0) {
                suggestionsDiv.innerHTML = `
                    <h4>💡 Improvement Suggestions:</h4>
                    <ul>
                        ${suggestions.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                `;
            }
            
            // Show result with animation
            resultDiv.style.display = 'block';
            resultDiv.classList.add('fade-in');
            
            // Color code based on level
            const colors = {
                1: '#00b894', 2: '#00a085', 3: '#fdcb6e', 4: '#e17055',
                5: '#fd79a8', 6: '#a29bfe', 7: '#636e72', 8: '#2d3436'
            };
            resultDiv.style.background = `linear-gradient(135deg, ${colors[level.level]} 0%, ${colors[level.level]}dd 100%)`;
        }
    }

    async saveBBEECalculation(data, score, level) {
        try {
            const response = await fetch('/api/bbee/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...data,
                    score: score,
                    level: level.level
                })
            });
            
            if (!response.ok) {
                console.warn('Failed to save B-BBEE calculation');
            }
        } catch (error) {
            console.error('Error saving B-BBEE calculation:', error);
        }
    }

    // Partner Management
    async loadPartnerData() {
        try {
            const response = await fetch('/api/bbee/partners');
            if (response.ok) {
                this.partnerData = await response.json();
            } else {
                // Fallback to mock data
                this.partnerData = this.getMockPartners();
            }
            this.displayPartners(this.partnerData);
        } catch (error) {
            console.error('Error loading partners:', error);
            this.partnerData = this.getMockPartners();
            this.displayPartners(this.partnerData);
        }
    }

    getMockPartners() {
        return [
            {
                id: 1,
                name: "Thabo Construction (Pty) Ltd",
                bbeeLevel: 1,
                specialties: ["Civil Engineering", "Infrastructure"],
                location: "Gauteng",
                capacity: "R500M+ projects",
                matchPercentage: 95,
                contactEmail: "info@thaboconstruction.co.za",
                verified: true
            },
            {
                id: 2,
                name: "Nomsa Tech Solutions",
                bbeeLevel: 2,
                specialties: ["IT Services", "Software Development"],
                location: "Western Cape",
                capacity: "R100M+ projects",
                matchPercentage: 88,
                contactEmail: "hello@nomsatech.co.za",
                verified: true
            },
            {
                id: 3,
                name: "Ubuntu Consulting Group",
                bbeeLevel: 1,
                specialties: ["Management Consulting", "Strategy"],
                location: "KwaZulu-Natal",
                capacity: "R50M+ projects",
                matchPercentage: 82,
                contactEmail: "contact@ubuntu-consulting.co.za",
                verified: true
            },
            {
                id: 4,
                name: "Amandla Engineering",
                bbeeLevel: 3,
                specialties: ["Mechanical Engineering", "Mining"],
                location: "Limpopo",
                capacity: "R200M+ projects",
                matchPercentage: 76,
                contactEmail: "info@amandlaeng.co.za",
                verified: false
            }
        ];
    }

    displayPartners(partners) {
        const container = document.getElementById('partnerCards');
        if (!container) return;
        
        container.innerHTML = partners.map(partner => `
            <div class="partner-card" data-partner-id="${partner.id}">
                <div class="partner-info">
                    <div class="partner-name">
                        ${partner.name}
                        ${partner.verified ? '<i class="fas fa-check-circle" style="color: #00b894; margin-left: 5px;" title="Verified"></i>' : ''}
                    </div>
                    <div class="partner-level">Level ${partner.bbeeLevel} B-BBEE</div>
                </div>
                <div class="match-percentage">${partner.matchPercentage}% Match</div>
                <div class="partner-details">
                    <strong>Specialties:</strong> ${partner.specialties.join(', ')}<br>
                    <strong>Location:</strong> ${partner.location}<br>
                    <strong>Capacity:</strong> ${partner.capacity}
                </div>
                <button class="action-btn" onclick="bbeeApp.connectPartner(${partner.id})">
                    <i class="fas fa-handshake"></i> Connect Now
                </button>
            </div>
        `).join('');
    }

    searchPartners(query = '') {
        if (!query.trim()) {
            this.displayPartners(this.partnerData);
            return;
        }
        
        const filtered = this.partnerData.filter(partner => 
            partner.name.toLowerCase().includes(query.toLowerCase()) ||
            partner.specialties.some(s => s.toLowerCase().includes(query.toLowerCase())) ||
            partner.location.toLowerCase().includes(query.toLowerCase()) ||
            `level ${partner.bbeeLevel}`.includes(query.toLowerCase())
        );
        
        this.displayPartners(filtered);
    }

    async connectPartner(partnerId) {
        const partner = this.partnerData.find(p => p.id === partnerId);
        if (!partner) return;
        
        if (confirm(`Connect with ${partner.name}?\n\nThis will send a partnership request and share your company information.`)) {
            try {
                const response = await fetch('/api/bbee/connect-partner', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        partnerId: partnerId,
                        message: `Partnership request for upcoming tenders`
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✅ Partnership request sent to ${partner.name}!\n\nThey will be notified and can respond via email.`);
                    this.trackEvent('partner_connection_sent', { partnerId, partnerName: partner.name });
                } else {
                    alert('❌ Failed to send partnership request. Please try again.');
                }
            } catch (error) {
                console.error('Error connecting partner:', error);
                alert('❌ Network error. Please check your connection and try again.');
            }
        }
    }

    // Utility Functions
    trackEvent(eventName, data = {}) {
        // Analytics tracking
        if (typeof gtag !== 'undefined') {
            gtag('event', eventName, data);
        }
        
        // Internal tracking
        fetch('/api/analytics/track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event: eventName, data: data })
        }).catch(console.error);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-ZA', {
            style: 'currency',
            currency: 'ZAR',
            minimumFractionDigits: 0
        }).format(amount);
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Global functions for button onclick handlers
function showCalculator() {
    bbeeApp.showSection('calculator');
    bbeeApp.trackEvent('section_viewed', { section: 'calculator' });
}

function showPartnershipFinder() {
    bbeeApp.showSection('partnership');
    bbeeApp.trackEvent('section_viewed', { section: 'partnership' });
}

function showIntegrations() {
    bbeeApp.showSection('integration');
    bbeeApp.trackEvent('section_viewed', { section: 'integration' });
}

function showTracker() {
    bbeeApp.showSection('tracker');
    bbeeApp.trackEvent('section_viewed', { section: 'tracker' });
}

function calculateBBEE() {
    bbeeApp.calculateBBEE();
    bbeeApp.trackEvent('bbee_calculation', {
        blackOwnership: bbeeApp.getInputValue('blackOwnership'),
        blackManagement: bbeeApp.getInputValue('blackManagement')
    });
}

function searchPartners() {
    const query = document.getElementById('partnerSearch')?.value || '';
    bbeeApp.searchPartners(query);
    bbeeApp.trackEvent('partner_search', { query });
}

// Initialize the application
let bbeeApp;
document.addEventListener('DOMContentLoaded', function() {
    bbeeApp = new BBEEPlatform();
    
    // Add notification styles if not already present
    if (!document.querySelector('#notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                color: #333;
                padding: 15px 20px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 10000;
                max-width: 400px;
                animation: slideInRight 0.3s ease;
            }
            
            .notification-info { border-left: 5px solid #3498db; }
            .notification-success { border-left: 5px solid #27ae60; }
            .notification-warning { border-left: 5px solid #f39c12; }
            .notification-error { border-left: 5px solid #e74c3c; }
            
            .notification-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .notification-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                margin-left: 15px;
                opacity: 0.7;
            }
            
            .notification-close:hover {
                opacity: 1;
            }
            
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(styles);
    }
});