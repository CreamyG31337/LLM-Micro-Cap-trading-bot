/**
 * Theme Manager for Portfolio Dashboard
 * Handles theme switching, persistence, and API synchronization
 */

class ThemeManager {
    constructor() {
        this.currentTheme = this.loadTheme();
        this.listeners = [];
        this.init();
    }

    /**
     * Initialize the theme manager
     */
    init() {
        // Apply the saved theme on page load
        this.applyTheme(this.currentTheme);

        // Listen for theme changes from other tabs/windows
        window.addEventListener('storage', (e) => {
            if (e.key === 'theme') {
                this.currentTheme = e.newValue || 'system';
                this.applyTheme(this.currentTheme, false); // Don't save again
            }
        });
    }

    /**
     * Load theme from localStorage
     * @returns {string} The saved theme or 'system' as default
     */
    loadTheme() {
        return localStorage.getItem('theme') || 'system';
    }

    /**
     * Set the current theme
     * @param {string} theme - Theme name ('system', 'light', 'dark', 'midnight-tokyo', 'abyss')
     */
    async setTheme(theme) {
        const validThemes = ['system', 'light', 'dark', 'midnight-tokyo', 'abyss'];
        if (!validThemes.includes(theme)) {
            console.error(`Invalid theme: ${theme}`);
            return;
        }

        this.currentTheme = theme;
        this.applyTheme(theme);
    }

    /**
     * Apply theme to the page
     * @param {string} theme - Theme to apply
     * @param {boolean} persist - Whether to persist to localStorage and API
     */
    applyTheme(theme, persist = true) {
        // Update data-theme attribute on the HTML element
        document.documentElement.setAttribute('data-theme', theme);

        // Toggle 'dark' class for Tailwind dark mode support
        const darkThemes = ['dark', 'midnight-tokyo', 'abyss'];
        if (darkThemes.includes(theme) || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

        if (persist) {
            // Save to localStorage
            localStorage.setItem('theme', theme);

            // Sync to backend API
            this.syncToBackend(theme);
        }

        // Notify listeners (e.g., charts that need to update)
        this.notifyListeners(theme);
    }

    /**
     * Sync theme preference to backend
     * @param {string} theme - Theme to save
     */
    async syncToBackend(theme) {
        try {
            const response = await fetch('/api/settings/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ theme })
            });

            if (!response.ok) {
                console.warn('Failed to sync theme to backend:', response.statusText);
            }
        } catch (error) {
            console.error('Error syncing theme to backend:', error);
        }
    }

    /**
     * Add a listener for theme changes
     * @param {function} callback - Function to call when theme changes
     */
    addListener(callback) {
        this.listeners.push(callback);
    }

    /**
     * Remove a listener
     * @param {function} callback - Function to remove
     */
    removeListener(callback) {
        this.listeners = this.listeners.filter(cb => cb !== callback);
    }

    /**
     * Notify all listeners of theme change
     * @param {string} theme - New theme
     */
    notifyListeners(theme) {
        this.listeners.forEach(callback => {
            try {
                callback(theme);
            } catch (error) {
                console.error('Error in theme listener:', error);
            }
        });
    }

    /**
     * Get the current theme
     * @returns {string} Current theme
     */
    getTheme() {
        return this.currentTheme;
    }

    /**
     * Get the effective theme (resolves 'system' to actual dark/light)
     * @returns {string} Effective theme ('light', 'dark', 'midnight-tokyo', 'abyss')
     */
    getEffectiveTheme() {
        if (this.currentTheme === 'system') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return this.currentTheme;
    }
}

// Create global instance
window.themeManager = new ThemeManager();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}
