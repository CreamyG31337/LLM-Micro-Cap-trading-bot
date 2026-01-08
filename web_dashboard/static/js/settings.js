// Settings page AJAX handlers

function showSuccess(elementId) {
    const element = document.getElementById(elementId);
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 3000);
}

function showError(elementId) {
    const element = document.getElementById(elementId);
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

// Timezone save handler
document.addEventListener('DOMContentLoaded', function () {
    const saveTimezoneBtn = document.getElementById('save-timezone');
    if (saveTimezoneBtn) {
        saveTimezoneBtn.addEventListener('click', function () {
            const timezone = document.getElementById('timezone-select').value;

            fetch('/api/settings/timezone', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ timezone: timezone })
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.error || `HTTP ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        showSuccess('timezone-success');
                    } else {
                        console.error('Timezone save failed:', data.error);
                        showError('timezone-error');
                    }
                })
                .catch(error => {
                    console.error('Error saving timezone:', error);
                    showError('timezone-error');
                });
        });
    }

    // Currency save handler
    const saveCurrencyBtn = document.getElementById('save-currency');
    if (saveCurrencyBtn) {
        saveCurrencyBtn.addEventListener('click', function () {
            const currency = document.getElementById('currency-select').value;

            fetch('/api/settings/currency', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ currency: currency })
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.error || `HTTP ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        showSuccess('currency-success');
                    } else {
                        console.error('Currency save failed:', data.error);
                        showError('currency-error');
                    }
                })
                .catch(error => {
                    console.error('Error saving currency:', error);
                    showError('currency-error');
                });
        });
    }

    // Theme auto-save on change
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        // Store original theme for error recovery (use let so we can update it)
        let originalTheme = document.documentElement.getAttribute('data-theme') || 'system';
        
        themeSelect.addEventListener('change', function () {
            const theme = this.value;
            const selectElement = this; // Capture 'this' for use in callbacks
            
            // Apply theme immediately (optimistic update)
            document.documentElement.setAttribute('data-theme', theme);
            
            // Save to server
            fetch('/api/settings/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ theme: theme })
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.error || `HTTP ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        showSuccess('theme-success');
                        // Update original theme for next error recovery
                        originalTheme = theme;
                    } else {
                        console.error('Theme save failed:', data.error);
                        // Revert on error
                        document.documentElement.setAttribute('data-theme', originalTheme);
                        selectElement.value = originalTheme;
                        showError('theme-error');
                    }
                })
                .catch(error => {
                    console.error('Error saving theme:', error);
                    // Revert on error
                    document.documentElement.setAttribute('data-theme', originalTheme);
                    selectElement.value = originalTheme;
                    showError('theme-error');
                });
        });
    }
});
