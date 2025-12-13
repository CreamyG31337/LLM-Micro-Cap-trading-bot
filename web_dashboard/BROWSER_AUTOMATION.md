# Browser Automation for Streamlit Dashboard

## What is an Accessibility Tree?

The **accessibility tree** is a simplified representation of a web page's structure that's used by:
- Screen readers (for visually impaired users)
- Browser automation tools (like the ones used by AI assistants)
- Assistive technologies

It's derived from the DOM (Document Object Model) but simplified to focus on interactive elements and their semantic meaning. For example:
- A `<button>` becomes a "button" role
- An `<input type="text">` becomes a "textbox" role
- A `<form>` becomes a "form" role

## Why Streamlit Forms Are Tricky

Streamlit dynamically generates complex, nested DOM structures. When you write:

```python
st.text_input("Email", type="default")
```

Streamlit creates:
- A label element
- A wrapper div
- The actual input element (deeply nested)
- Styling elements
- Event handlers

The accessibility tree might show these as generic "generic" containers rather than direct "textbox" elements, making it hard for automation tools to find and interact with them.

## Solutions

### Option 1: Add Explicit Keys (Current Approach)

We already use `key` parameters in some places, which helps Streamlit identify components:

```python
email = st.text_input("Email", type="default", key="login_email")
password = st.text_input("Password", type="password", key="login_password")
```

**Status**: Already implemented in register form, but not in login form.

### Option 2: Use CSS Selectors (More Reliable)

Instead of relying on the accessibility tree, we could:
1. Inspect the actual DOM structure
2. Use CSS selectors to find inputs
3. Target inputs by their `name` or `id` attributes

**Limitation**: The current browser tools don't support CSS selectors directly.

### Option 3: Direct API Testing (Best for Automated Tests)

For automated testing, bypass the browser entirely:

```python
from auth_utils import login_user

# Direct API call - no browser needed
result = login_user("guest.test@tradingbot.local", "^f26z4u^swiX313s6zhB")
if result and "access_token" in result:
    print("Login successful!")
```

**Advantage**: Fast, reliable, doesn't depend on UI rendering.

### Option 4: Selenium with Explicit Waits

Use Selenium WebDriver with explicit waits for elements:

```python
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Wait for input to be present
email_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
)
email_input.send_keys("guest.test@tradingbot.local")
```

**Advantage**: More control, can target by CSS selectors, XPath, etc.

## Recommended Approach

For **AI agent browser testing** (current use case):
- The current browser tools work best for **visual verification** and **navigation**
- For **form filling**, manual testing or direct API calls are more reliable
- We can improve by adding explicit `key` parameters to all form inputs

For **automated testing** (CI/CD):
- Use direct API calls (`auth_utils.login_user()`) instead of browser automation
- Faster, more reliable, doesn't depend on UI rendering

## Current Status

✅ **Test accounts created and working** - credentials saved to `test_credentials.json`
✅ **Manual login works** - accounts are functional
⚠️ **Browser automation limited** - Streamlit's dynamic DOM makes form filling unreliable

## Next Steps

1. Add explicit `key` parameters to login form inputs (may help)
2. Document that manual testing or API calls are preferred for login testing
3. Consider adding a test script that uses direct API calls for automated testing

