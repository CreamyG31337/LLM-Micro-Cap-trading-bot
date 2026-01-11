/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./static/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                // Semantic color names that map to CSS variables
                'dashboard': {
                    'background': 'var(--bg-secondary)',
                    'surface': 'var(--bg-primary)',
                    'surface-alt': 'var(--bg-tertiary)',
                },
                'text': {
                    'primary': 'var(--text-primary)',
                    'secondary': 'var(--text-secondary)',
                    'tertiary': 'var(--text-tertiary)',
                },
                'accent': {
                    'from': 'var(--gradient-from)',
                    'to': 'var(--gradient-to)',
                },
                'border': {
                    'DEFAULT': 'var(--border-color)',
                    'hover': 'var(--border-hover)',
                }
            },
        },
    },
    plugins: [],
}
