import re
import sys

# Force UTF-8 output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Read the file
with open('web_dashboard/pages/admin.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all st.rerun() lines
rerun_lines = []
for i, line in enumerate(lines):
    if 'st.rerun()' in line:
        rerun_lines.append(i)

# Check lines before each rerun
print("Checking for success/error/warning messages before st.rerun():\n")
print("="*80)

for ln in rerun_lines:
    # Look at the 5 lines before st.rerun()
    context_start = max(0, ln - 5)
    context = lines[context_start:ln+1]
    
    # Check if any of these lines have st.success, st.error, st.warning
    has_message = False
    message_line = None
    for i, ctx_line in enumerate(context):
        if any(msg in ctx_line for msg in ['st.success', 'st.error', 'st.warning', 'st.info']):
            has_message = True
            message_line = context_start + i + 1
            break
    
    if has_message:
        print(f"\n[!] ISSUE FOUND - Line {ln+1} (st.rerun):")
        print(f"   Message at line {message_line}: {lines[message_line-1].strip()}")
        print("   Context:")
        for i, ctx_line in enumerate(context):
            line_num = context_start + i + 1
            prefix = ">>> " if line_num == message_line or line_num == ln+1 else "    "
            print(f"   {prefix}{line_num}: {ctx_line.rstrip()}")

print("\n" + "="*80)
print("\nSearch complete!")
