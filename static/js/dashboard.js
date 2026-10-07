/**
 * Dashboard Utility Functions
 * Shared JavaScript functionality for the Blockchain Analytics Dashboard
 */

// Global variables
let globalRefreshInterval;
let globalCharts = {};

// Initialize dashboard common functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializePopovers();
    setupGlobalErrorHandling();
    setupAutoRefresh();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap popovers
 */
function initializePopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Setup global error handling
 */
function setupGlobalErrorHandling() {
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        showNotification('An unexpected error occurred. Please refresh the page.', 'danger');
    });
}

/**
 * Setup auto-refresh functionality
 */
function setupAutoRefresh() {
    // Auto-refresh every 5 minutes for all pages
    globalRefreshInterval = setInterval(() => {
        if (typeof refreshData === 'function') {
            refreshData();
        }
    }, 300000);
}

/**
 * Show notification toast
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, danger, warning, info)
 * @param {number} duration - Duration in milliseconds (default: 5000)
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center text-bg-${type} border-0`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button"  class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastElement);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastElement, { delay: duration });
    toast.show();
    
    // Remove element after hiding
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Format currency values
 * @param {number} value - The numeric value
 * @param {string} currency - Currency code (default: USD)
 * @param {boolean} compact - Use compact notation
 * @returns {string} Formatted currency string
 */
function formatCurrency(value, currency = 'USD', compact = true) {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    
    const options = {
        style: 'currency',
        currency: currency,
        maximumFractionDigits: value < 1 ? 6 : 2
    };
    
    if (compact && Math.abs(value) >= 1000) {
        options.notation = 'compact';
    }
    
    return new Intl.NumberFormat('en-US', options).format(value);
}

/**
 * Format number values
 * @param {number} value - The numeric value
 * @param {boolean} compact - Use compact notation
 * @returns {string} Formatted number string
 */
function formatNumber(value, compact = true) {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    
    const options = {
        maximumFractionDigits: 1
    };
    
    if (compact && Math.abs(value) >= 1000) {
        options.notation = 'compact';
    }
    
    return new Intl.NumberFormat('en-US', options).format(value);
}

/**
 * Format percentage values
 * @param {number} value - The numeric value
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted percentage string
 */
function formatPercentage(value, decimals = 2) {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Get color class based on value change
 * @param {number} value - The numeric value
 * @returns {string} CSS class name
 */
function getChangeColorClass(value) {
    if (value > 0) return 'text-success';
    if (value < 0) return 'text-danger';
    return 'text-muted';
}

/**
 * Get badge class based on value change
 * @param {number} value - The numeric value
 * @returns {string} CSS class name
 */
function getChangeBadgeClass(value) {
    if (value > 0) return 'bg-success';
    if (value < 0) return 'bg-danger';
    return 'bg-secondary';
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
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

/**
 * Throttle function
 * @param {Function} func - Function to throttle
 * @param {number} limit - Limit in milliseconds
 * @returns {Function} Throttled function
 */
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

/**
 * Safe API fetch with error handling
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options
 * @returns {Promise} Promise that resolves to response data
 */
async function safeFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            timeout: 30000,
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        return data;
    } catch (error) {
        console.error('API fetch error:', error);
        showNotification(`API Error: ${error.message}`, 'danger');
        throw error;
    }
}

/**
 * Create a loading spinner
 * @param {string} size - Size of spinner (sm, md, lg)
 * @returns {HTMLElement} Spinner element
 */
function createLoadingSpinner(size = 'md') {
    const spinner = document.createElement('div');
    spinner.className = `d-flex justify-content-center align-items-center p-4`;
    
    const sizeClass = size === 'sm' ? 'spinner-border-sm' : '';
    
    spinner.innerHTML = `
        <div class="spinner-border text-primary ${sizeClass}" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    
    return spinner;
}

/**
 * Show loading state for an element
 * @param {HTMLElement|string} element - Element or selector
 * @param {boolean} show - Show or hide loading
 */
function showElementLoading(element, show = true) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (!el) return;
    
    if (show) {
        el.dataset.originalContent = el.innerHTML;
        el.innerHTML = '';
        el.appendChild(createLoadingSpinner('sm'));
        el.classList.add('loading-state');
    } else {
        if (el.dataset.originalContent) {
            el.innerHTML = el.dataset.originalContent;
            delete el.dataset.originalContent;
        }
        el.classList.remove('loading-state');
    }
}

/**
 * Animate number counting effect
 * @param {HTMLElement} element - Target element
 * @param {number} start - Start value
 * @param {number} end - End value
 * @param {number} duration - Animation duration in milliseconds
 * @param {Function} formatter - Optional formatter function
 */
function animateNumber(element, start, end, duration = 1000, formatter = null) {
    const startTime = Date.now();
    const difference = end - start;
    
    function updateNumber() {
        const now = Date.now();
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = start + (difference * easeOut);
        
        if (formatter) {
            element.textContent = formatter(current);
        } else {
            element.textContent = Math.round(current).toLocaleString();
        }
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    requestAnimationFrame(updateNumber);
}

/**
 * Chart utility functions
 */
const ChartUtils = {
    /**
     * Default chart colors
     */
    colors: {
        primary: '#0d6efd',
        success: '#198754',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#0dcaf0',
        secondary: '#6c757d'
    },
    
    /**
     * Get responsive chart options
     * @param {Object} customOptions - Custom options to merge
     * @returns {Object} Chart options
     */
    getResponsiveOptions(customOptions = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        };
        
        return this.mergeDeep(defaultOptions, customOptions);
    },
    
    /**
     * Deep merge objects
     * @param {Object} target - Target object
     * @param {Object} source - Source object
     * @returns {Object} Merged object
     */
    mergeDeep(target, source) {
        const result = { ...target };
        
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this.mergeDeep(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        
        return result;
    },
    
    /**
     * Destroy chart safely
     * @param {Chart} chart - Chart.js instance
     */
    destroyChart(chart) {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    },
    
    /**
     * Generate gradient for chart
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {string} color1 - Start color
     * @param {string} color2 - End color
     * @returns {CanvasGradient} Gradient object
     */
    createGradient(ctx, color1, color2) {
        const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    }
};

/**
 * Local storage utilities
 */
const StorageUtils = {
    /**
     * Get item from localStorage with JSON parsing
     * @param {string} key - Storage key
     * @param {*} defaultValue - Default value if key doesn't exist
     * @returns {*} Stored value or default
     */
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return defaultValue;
        }
    },
    
    /**
     * Set item in localStorage with JSON serialization
     * @param {string} key - Storage key
     * @param {*} value - Value to store
     * @returns {boolean} Success status
     */
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Error writing to localStorage:', error);
            return false;
        }
    },
    
    /**
     * Remove item from localStorage
     * @param {string} key - Storage key
     */
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Error removing from localStorage:', error);
        }
    },
    
    /**
     * Clear all localStorage
     */
    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Error clearing localStorage:', error);
        }
    }
};

/**
 * Date utilities
 */
const DateUtils = {
    /**
     * Format date to relative time
     * @param {Date|string|number} date - Date to format
     * @returns {string} Relative time string
     */
    formatRelative(date) {
        const now = new Date();
        const targetDate = new Date(date);
        const diffInSeconds = Math.floor((now - targetDate) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)} days ago`;
        
        return targetDate.toLocaleDateString();
    },
    
    /**
     * Format timestamp to local string
     * @param {number} timestamp - Unix timestamp (ms)
     * @returns {string} Formatted date string
     */
    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    },
    
    /**
     * Get time ago string
     * @param {Date|string|number} date - Date to compare
     * @returns {string} Time ago string
     */
    timeAgo(date) {
        const now = new Date();
        const past = new Date(date);
        const diff = now - past;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return `${seconds}s ago`;
    }
};

// Export utilities for use in other scripts
window.DashboardUtils = {
    formatCurrency,
    formatNumber,
    formatPercentage,
    getChangeColorClass,
    getChangeBadgeClass,
    showNotification,
    safeFetch,
    createLoadingSpinner,
    showElementLoading,
    animateNumber,
    debounce,
    throttle,
    ChartUtils,
    StorageUtils,
    DateUtils
};

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (globalRefreshInterval) {
        clearInterval(globalRefreshInterval);
    }
    
    // Destroy all charts
    Object.values(globalCharts).forEach(chart => {
        ChartUtils.destroyChart(chart);
    });
});

console.log('Dashboard utilities loaded successfully');