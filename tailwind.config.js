/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./web_dashboard/templates/**/*.html",
    "./web_dashboard/static/**/*.js",
    // Include any Python files that might contain Tailwind classes in strings
    "./web_dashboard/**/*.py",
  ],
  theme: {
    extend: {
      // Custom theme extensions can be added here
      // For example: colors, spacing, fonts, etc.
    },
  },
  plugins: [
    // Add Tailwind plugins here if needed
    // Example: require('@tailwindcss/typography'),
  ],
}
