// Theme Manager - Handles light/dark theme switching with user persistence
class ThemeManager {
    constructor() {
        this.currentTheme = 'dark'; // Default theme
        this.themeToggleBtn = null;
        this.init();
    }

    init() {
        console.log('🎨 ThemeManager initializing...');
        
        // Load saved theme preference
        this.loadThemePreference();
        
        // Apply theme to document
        this.applyTheme(this.currentTheme);
        
        // Set up theme toggle button
        this.setupThemeToggle();
        
        // Listen for system theme changes
        this.setupSystemThemeListener();
        
        console.log(`✅ ThemeManager initialized with theme: ${this.currentTheme}`);
    }

    loadThemePreference() {
        try {
            // Check for user-specific theme preference first
            if (window.currentUser && window.currentUser.user_id) {
                const userThemeKey = `mefapex_theme_${window.currentUser.user_id}`;
                const userTheme = localStorage.getItem(userThemeKey);
                if (userTheme && (userTheme === 'light' || userTheme === 'dark')) {
                    this.currentTheme = userTheme;
                    console.log(`🎨 Loaded user-specific theme: ${userTheme}`);
                    return;
                }
            }
            
            // Fall back to global theme preference
            const globalTheme = localStorage.getItem('mefapex_theme');
            if (globalTheme && (globalTheme === 'light' || globalTheme === 'dark')) {
                this.currentTheme = globalTheme;
                console.log(`🎨 Loaded global theme: ${globalTheme}`);
                return;
            }
            
            // Check system preference as final fallback
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
                this.currentTheme = 'light';
                console.log('🎨 Using system preference: light');
            } else {
                this.currentTheme = 'dark';
                console.log('🎨 Using default theme: dark');
            }
        } catch (error) {
            console.warn('⚠️ Error loading theme preference:', error);
            this.currentTheme = 'dark';
        }
    }

    saveThemePreference(theme) {
        try {
            // Save user-specific preference if logged in
            if (window.currentUser && window.currentUser.user_id) {
                const userThemeKey = `mefapex_theme_${window.currentUser.user_id}`;
                localStorage.setItem(userThemeKey, theme);
                console.log(`💾 Saved user-specific theme: ${theme}`);
            }
            
            // Always save global preference as fallback
            localStorage.setItem('mefapex_theme', theme);
            console.log(`💾 Saved global theme: ${theme}`);
        } catch (error) {
            console.warn('⚠️ Error saving theme preference:', error);
        }
    }

    applyTheme(theme) {
        const html = document.documentElement;
        html.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        
        // Update theme toggle button appearance
        this.updateThemeToggleIcon(theme);
        
        console.log(`🎨 Applied theme: ${theme}`);
    }

    setupThemeToggle() {
        this.themeToggleBtn = document.getElementById('themeToggle');
        
        if (this.themeToggleBtn) {
            this.themeToggleBtn.addEventListener('click', () => this.toggleTheme());
            this.themeToggleBtn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
            
            // Set initial icon
            this.updateThemeToggleIcon(this.currentTheme);
            
            console.log('✅ Theme toggle button setup complete');
        } else {
            console.warn('⚠️ Theme toggle button not found');
        }
    }

    updateThemeToggleIcon(theme) {
        if (this.themeToggleBtn) {
            if (theme === 'dark') {
                this.themeToggleBtn.textContent = '☀️';
                this.themeToggleBtn.setAttribute('aria-label', 'Açık temaya geç');
                this.themeToggleBtn.setAttribute('title', 'Açık temaya geçiş yapın');
            } else {
                this.themeToggleBtn.textContent = '🌙';
                this.themeToggleBtn.setAttribute('aria-label', 'Koyu temaya geç');
                this.themeToggleBtn.setAttribute('title', 'Koyu temaya geçiş yapın');
            }
        }
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
        this.saveThemePreference(newTheme);
        
        // Announce theme change to screen readers
        this.announceThemeChange(newTheme);
        
        console.log(`🔄 Theme toggled from ${this.currentTheme === 'dark' ? 'light' : 'dark'} to ${newTheme}`);
    }

    announceThemeChange(theme) {
        // Create a temporary announcement for screen readers
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = `Tema ${theme === 'dark' ? 'koyu' : 'açık'} olarak değiştirildi`;
        
        document.body.appendChild(announcement);
        
        // Remove the announcement after screen readers have processed it
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }

    setupSystemThemeListener() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            mediaQuery.addEventListener('change', (e) => {
                // Only auto-change if user hasn't set a specific preference
                const hasUserPreference = localStorage.getItem('mefapex_theme') || 
                    (window.currentUser && localStorage.getItem(`mefapex_theme_${window.currentUser.user_id}`));
                
                if (!hasUserPreference) {
                    const systemTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(systemTheme);
                    console.log(`🔄 System theme changed to: ${systemTheme}`);
                }
            });
        }
    }

    // Method to refresh theme when user logs in/out
    refreshForUser() {
        this.loadThemePreference();
        this.applyTheme(this.currentTheme);
        console.log(`🔄 Theme refreshed for user change: ${this.currentTheme}`);
    }

    // Get current theme
    getCurrentTheme() {
        return this.currentTheme;
    }
}

// Initialize theme manager when DOM is ready
let themeManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        themeManager = new ThemeManager();
        window.themeManager = themeManager;
    });
} else {
    themeManager = new ThemeManager();
    window.themeManager = themeManager;
}

// Export for use in other modules
window.ThemeManager = ThemeManager;
