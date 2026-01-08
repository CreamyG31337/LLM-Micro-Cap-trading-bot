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
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showSuccess('timezone-success');
                    } else {
                        showError('timezone-error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
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
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showSuccess('currency-success');
                    } else {
                        showError('currency-error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showError('currency-error');
                });
        });
    }

    // Theme save handler
    const saveThemeBtn = document.getElementById('save-theme');
    if (saveThemeBtn) {
        saveThemeBtn.addEventListener('click', function () {
            const theme = document.getElementById('theme-select').value;

            fetch('/api/settings/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ theme: theme })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Apply theme immediately by updating data-theme attribute
                        document.documentElement.setAttribute('data-theme', theme);
                        showSuccess('theme-success');
                    } else {
                        showError('theme-error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showError('theme-error');
                });
        });
    }
});
