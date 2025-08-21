// Accessibility Manager - Handles keyboard navigation, focus management, and ARIA updates
class AccessibilityManager {
    constructor() {
        this.focusableElements = [];
        this.trapFocus = false;
        this.lastFocusedElement = null;
        this.init();
    }

    init() {
        console.log('♿ AccessibilityManager initializing...');
        
        // Set up keyboard navigation
        this.setupKeyboardNavigation();
        
        // Set up focus management
        this.setupFocusManagement();
        
        // Set up ARIA live regions
        this.setupLiveRegions();
        
        // Set up skip links
        this.setupSkipLinks();
        
        console.log('✅ AccessibilityManager initialized');
    }

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => this.handleGlobalKeydown(e));
        
        // Enhanced Enter and Space key handling for buttons
        document.addEventListener('keydown', (e) => {
            if ((e.key === 'Enter' || e.key === ' ') && 
                (e.target.tagName === 'BUTTON' || e.target.getAttribute('role') === 'button')) {
                if (e.key === ' ') {
                    e.preventDefault(); // Prevent page scroll on spacebar
                }
                e.target.click();
            }
        });
    }

    handleGlobalKeydown(e) {
        switch (e.key) {
            case 'Escape':
                this.handleEscape();
                break;
            case 'Tab':
                if (this.trapFocus) {
                    this.handleTabInTrap(e);
                }
                break;
            case 'F1':
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.showKeyboardShortcuts();
                }
                break;
        }
    }

    handleEscape() {
        // Close sidebar if open
        const sidebar = document.getElementById('chatHistorySidebar');
        if (sidebar && sidebar.style.transform === 'translateX(0px)') {
            window.closeChatHistorySidebar();
            return;
        }
        
        // Focus message input if in chat
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        if (chatContainer && chatContainer.style.display !== 'none' && messageInput) {
            messageInput.focus();
        }
    }

    setupFocusManagement() {
        // Track focus for better UX
        document.addEventListener('focusin', (e) => {
            this.lastFocusedElement = e.target;
        });

        // Improve focus visibility
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-nav');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-nav');
        });
    }

    // Focus trap for modal-like elements (sidebar)
    enableFocusTrap(container) {
        this.trapFocus = true;
        this.focusableElements = this.getFocusableElements(container);
        
        if (this.focusableElements.length > 0) {
            this.focusableElements[0].focus();
        }
    }

    disableFocusTrap() {
        this.trapFocus = false;
        this.focusableElements = [];
        
        // Return focus to last focused element before trap
        if (this.lastFocusedElement && document.contains(this.lastFocusedElement)) {
            this.lastFocusedElement.focus();
        }
    }

    handleTabInTrap(e) {
        if (this.focusableElements.length === 0) return;

        const firstElement = this.focusableElements[0];
        const lastElement = this.focusableElements[this.focusableElements.length - 1];

        if (e.shiftKey) {
            // Shift + Tab
            if (document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            }
        } else {
            // Tab
            if (document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    }

    getFocusableElements(container) {
        const focusableSelectors = [
            'button:not([disabled])',
            'input:not([disabled])',
            'textarea:not([disabled])',
            'select:not([disabled])',
            'a[href]',
            '[tabindex]:not([tabindex="-1"])',
            '[contenteditable="true"]'
        ].join(', ');

        return Array.from(container.querySelectorAll(focusableSelectors))
            .filter(el => !el.hidden && el.offsetParent !== null);
    }

    setupLiveRegions() {
        // Enhance existing live regions
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.setAttribute('aria-live', 'polite');
            chatMessages.setAttribute('aria-atomic', 'false');
        }

        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.setAttribute('aria-live', 'polite');
        }

        const loginError = document.getElementById('loginError');
        if (loginError) {
            loginError.setAttribute('aria-live', 'assertive');
        }
    }

    setupSkipLinks() {
        // Create skip link for keyboard users
        const skipLink = document.createElement('a');
        skipLink.href = '#messageInput';
        skipLink.textContent = 'Ana içeriğe geç';
        skipLink.className = 'skip-link';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            background: var(--button-primary);
            color: white;
            padding: 8px;
            text-decoration: none;
            border-radius: 4px;
            z-index: 10000;
            transition: top 0.3s;
        `;

        skipLink.addEventListener('focus', () => {
            skipLink.style.top = '6px';
        });

        skipLink.addEventListener('blur', () => {
            skipLink.style.top = '-40px';
        });

        document.body.insertBefore(skipLink, document.body.firstChild);
    }

    // Announce messages to screen readers
    announceMessage(message, type = 'polite') {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', type);
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            if (document.body.contains(announcement)) {
                document.body.removeChild(announcement);
            }
        }, 1000);
    }

    // Update message count for screen readers
    updateMessageCount() {
        const messages = document.querySelectorAll('.message');
        const chatMessages = document.getElementById('chatMessages');
        
        if (chatMessages && messages.length > 0) {
            chatMessages.setAttribute('aria-label', 
                `Sohbet mesajları, ${messages.length} mesaj`);
        }
    }

    // Improve button accessibility
    enhanceButtonAccessibility(button, description) {
        if (!button) return;
        
        // Ensure minimum touch target size
        const rect = button.getBoundingClientRect();
        if (rect.width < 44 || rect.height < 44) {
            button.style.minWidth = '44px';
            button.style.minHeight = '44px';
        }
        
        // Add description if provided
        if (description && !button.getAttribute('aria-label')) {
            button.setAttribute('aria-label', description);
        }
    }

    showKeyboardShortcuts() {
        const shortcuts = [
            'Enter - Mesaj gönder',
            'Escape - Sidebar\'ı kapat veya mesaj kutusuna odaklan',
            'Tab - Sonraki elemana geç',
            'Shift+Tab - Önceki elemana geç',
            'Ctrl+F1 - Bu yardımı göster'
        ];

        this.announceMessage(`Klavye kısayolları: ${shortcuts.join(', ')}`, 'assertive');
    }

    // Handle sidebar focus management
    onSidebarOpen() {
        const sidebar = document.getElementById('chatHistorySidebar');
        if (sidebar) {
            this.enableFocusTrap(sidebar);
        }
    }

    onSidebarClose() {
        this.disableFocusTrap();
    }

    // Enhance form validation
    enhanceFormValidation() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const invalidFields = form.querySelectorAll(':invalid');
                if (invalidFields.length > 0) {
                    e.preventDefault();
                    invalidFields[0].focus();
                    this.announceMessage('Form hatası: Lütfen gerekli alanları doldurun', 'assertive');
                }
            });
        });
    }

    // Add loading states for better UX
    setLoadingState(element, isLoading, loadingText = 'Yükleniyor...') {
        if (!element) return;
        
        if (isLoading) {
            element.setAttribute('aria-busy', 'true');
            element.setAttribute('aria-live', 'polite');
            const originalText = element.textContent;
            element.setAttribute('data-original-text', originalText);
            element.textContent = loadingText;
        } else {
            element.removeAttribute('aria-busy');
            element.removeAttribute('aria-live');
            const originalText = element.getAttribute('data-original-text');
            if (originalText) {
                element.textContent = originalText;
                element.removeAttribute('data-original-text');
            }
        }
    }
}

// Initialize accessibility manager
let accessibilityManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        accessibilityManager = new AccessibilityManager();
        window.accessibilityManager = accessibilityManager;
    });
} else {
    accessibilityManager = new AccessibilityManager();
    window.accessibilityManager = accessibilityManager;
}

// Export for use in other modules
window.AccessibilityManager = AccessibilityManager;

// Add CSS for keyboard navigation
const style = document.createElement('style');
style.textContent = `
    /* Hide focus outlines by default */
    * {
        outline: none;
    }
    
    /* Show focus outlines only when using keyboard navigation */
    .keyboard-nav *:focus {
        outline: 2px solid var(--border-focus, #007bff);
        outline-offset: 2px;
    }
    
    .keyboard-nav button:focus,
    .keyboard-nav input:focus,
    .keyboard-nav textarea:focus {
        box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
    }
`;
document.head.appendChild(style);
