# Flowbite Integration Guide

## Overview

Flowbite is a Tailwind CSS component library that provides pre-built, mobile-responsive UI components. It's integrated into our Flask templates to enable:

- Mobile-responsive navigation with hamburger menus
- Dropdown menus and modals
- Consistent UI components across all Flask pages
- Better mobile experience without writing custom JavaScript

## Quick Start

All Flask templates should extend `base.html` which includes Flowbite automatically:

```jinja2
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
    <!-- Your page content here -->
{% endblock %}
```

## Components Available

### Navigation

The base template includes:
- **Hamburger menu** (mobile) - Top-left button that opens sidebar
- **User menu** (top-right) - Dropdown with Settings and Logout
- **Sidebar drawer** - Collapsible navigation menu (mobile) / persistent sidebar (desktop)

### Using Flowbite Components

Flowbite components work with data attributes. Examples:

#### Dropdown Menu
```html
<button id="dropdownButton" data-dropdown-toggle="dropdown">
    Dropdown button
</button>
<div id="dropdown" class="hidden">
    <a href="#">Item 1</a>
    <a href="#">Item 2</a>
</div>
```

#### Modal
```html
<button data-modal-target="modal" data-modal-toggle="modal">
    Open modal
</button>
<div id="modal" tabindex="-1" class="hidden">
    <!-- Modal content -->
</div>
```

#### Drawer (Sidebar)
```html
<button data-drawer-target="sidebar" data-drawer-toggle="sidebar">
    Toggle sidebar
</button>
<aside id="sidebar" class="fixed top-0 left-0 z-40 w-64 h-screen">
    <!-- Sidebar content -->
</aside>
```

## Mobile Responsiveness

### Breakpoints
- **Mobile**: `< 768px` - Hamburger menu, collapsible sidebar
- **Desktop**: `>= 768px` - Persistent sidebar, no hamburger

### Tables and Charts
For tables and charts that need horizontal scroll on mobile:

```html
<div class="overflow-x-auto">
    <table class="min-w-full">
        <!-- Table content -->
    </table>
</div>
```

For Plotly charts, they're already responsive, but you may want to add a note:

```html
<div class="mb-2 text-sm text-gray-500 md:hidden">
    💡 Tip: Rotate your device for better viewing
</div>
<div id="chart"></div>
```

## Navigation Links

The navigation uses `shared_navigation.py` to determine which links to show:

- Respects `v2_enabled` preference (shows Flask routes when enabled)
- Checks admin status (shows admin links for admins)
- Checks service availability (Postgres, Supabase, Ollama)

## Theme Support

The base template respects the `data-theme` attribute:
- `data-theme="dark"` - Dark mode
- `data-theme="light"` - Light mode  
- `data-theme="system"` - System default

Theme is set via user preferences and applied automatically.

## Customization

### Adding Custom Styles

Use the `extra_head` block:

```jinja2
{% block extra_head %}
<style>
    .custom-class {
        /* Your styles */
    }
</style>
{% endblock %}
```

### Adding Custom Scripts

Use the `extra_scripts` block:

```jinja2
{% block extra_scripts %}
<script>
    // Your JavaScript
</script>
{% endblock %}
```

## Resources

- [Flowbite Documentation](https://flowbite.com/docs/getting-started/introduction/)
- [Flowbite Components](https://flowbite.com/docs/components/accordion/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

## Migration Notes

When migrating existing templates:

1. Change `<!DOCTYPE html>` to `{% extends "base.html" %}`
2. Move `<head>` content to `{% block extra_head %}` (if needed)
3. Move `<body>` content to `{% block content %}`
4. Remove duplicate header/navigation code
5. Move scripts to `{% block extra_scripts %}`

Example migration:

**Before:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Settings</title>
</head>
<body>
    <header>...</header>
    <div>Content</div>
</body>
</html>
```

**After:**
```jinja2
{% extends "base.html" %}

{% block title %}Settings{% endblock %}

{% block content %}
    <div>Content</div>
{% endblock %}
```
