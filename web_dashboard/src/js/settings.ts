// Settings page AJAX handlers
console.log('Settings.js loaded successfully');

// Make this a module for proper scoping
export {};

// API Response interface
interface ApiResponse {
    success: boolean;
    error?: string;
}

// Settings API request interfaces
interface TimezoneRequest {
    timezone: string;
}

interface CurrencyRequest {
    currency: string;
}

interface ThemeRequest {
    theme: string;
}

/**
 * Show success message for a given element ID
 * @param elementId - The ID of the element to show
 */
function showSuccess(elementId: string): void {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'block';
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
}

/**
 * Show error message for a given element ID
 * @param elementId - The ID of the element to show
 * @param errorMessage - Optional error message to display
 */
function showError(elementId: string, errorMessage?: string): void {
    const element = document.getElementById(elementId);
    if (element) {
        // Update error message if provided
        if (errorMessage) {
            element.textContent = '❌ ' + errorMessage;
        }
        element.style.display = 'block';
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// Initialize event handlers when DOM is ready
document.addEventListener('DOMContentLoaded', function (): void {
    // Timezone auto-save handler
    const timezoneSelect = document.getElementById('timezone-select') as HTMLSelectElement | null;
    if (timezoneSelect) {
        let originalTimezone: string = timezoneSelect.value;

        timezoneSelect.addEventListener('change', function (this: HTMLSelectElement): void {
            const timezone = this.value;
            const selectElement = this;

            fetch('/api/settings/timezone', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ timezone: timezone } as TimezoneRequest)
            })
                .then((response: Response) => {
                    if (!response.ok) {
                        return response.json().then((data: ApiResponse) => {
                            throw new Error(data.error || `HTTP ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then((data: ApiResponse) => {
                    if (data.success) {
                        showSuccess('timezone-success');
                        originalTimezone = timezone;
                    } else {
                        const errorMsg = data.error || 'Failed to save timezone. Please try again.';
                        console.error('Timezone save failed:', errorMsg);
                        selectElement.value = originalTimezone; // Revert
                        showError('timezone-error', errorMsg);
                    }
                })
                .catch((error: Error) => {
                    const errorMsg = error.message || 'Error saving timezone. Please try again.';
                    console.error('Error saving timezone:', error);
                    selectElement.value = originalTimezone; // Revert
                    showError('timezone-error', errorMsg);
                });
        });
    }

    // Currency auto-save handler
    const currencySelect = document.getElementById('currency-select') as HTMLSelectElement | null;
    if (currencySelect) {
        let originalCurrency: string = currencySelect.value;

        currencySelect.addEventListener('change', function (this: HTMLSelectElement): void {
            const currency = this.value;
            const selectElement = this;

            fetch('/api/settings/currency', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ currency: currency } as CurrencyRequest)
            })
                .then((response: Response) => {
                    if (!response.ok) {
                        return response.json().then((data: ApiResponse) => {
                            throw new Error(data.error || `HTTP ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then((data: ApiResponse) => {
                    if (data.success) {
                        showSuccess('currency-success');
                        originalCurrency = currency;
                    } else {
                        const errorMsg = data.error || 'Failed to save currency. Please try again.';
                        console.error('Currency save failed:', errorMsg);
                        selectElement.value = originalCurrency; // Revert
                        showError('currency-error', errorMsg);
                    }
                })
                .catch((error: Error) => {
                    const errorMsg = error.message || 'Error saving currency. Please try again.';
                    console.error('Error saving currency:', error);
                    selectElement.value = originalCurrency; // Revert
                    showError('currency-error', errorMsg);
                });
        });
    }

    // Theme auto-save on change
    const themeSelect = document.getElementById('theme-select') as HTMLSelectElement | null;
    if (themeSelect) {
        // Store original theme for error recovery
        let originalTheme: string = document.documentElement.getAttribute('data-theme') || 'system';

        themeSelect.addEventListener('change', function (this: HTMLSelectElement): void {
            const theme: string = this.value;
            const selectElement: HTMLSelectElement = this; // Capture 'this' for use in callbacks

            // Apply theme immediately (optimistic update)
            document.documentElement.setAttribute('data-theme', theme);

            // Save to server
            fetch('/api/settings/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ theme: theme } as ThemeRequest)
            })
                .then((response: Response) => {
                    if (!response.ok) {
                        return response.json().then((data: ApiResponse) => {
                            throw new Error(data.error || `HTTP ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then((data: ApiResponse) => {
                    if (data.success) {
                        showSuccess('theme-success');
                        // Update original theme for next error recovery
                        originalTheme = theme;
                    } else {
                        const errorMsg = data.error || 'Failed to save theme. Please try again.';
                        console.error('Theme save failed:', errorMsg);
                        // Revert on error
                        document.documentElement.setAttribute('data-theme', originalTheme);
                        selectElement.value = originalTheme;
                        showError('theme-error', errorMsg);
                    }
                })
                .catch((error: Error) => {
                    const errorMsg = error.message || 'Error saving theme. Please try again.';
                    console.error('Error saving theme:', error);
                    // Revert on error
                    document.documentElement.setAttribute('data-theme', originalTheme);
                    selectElement.value = originalTheme;
                    showError('theme-error', errorMsg);
                });
        });
    }
});
