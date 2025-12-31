
from pathlib import Path

file_path = Path("data/committee-membership-current.yaml")
lines = file_path.read_text(encoding="utf-8").splitlines()

target_codes = ["HSGO:", "HSFA:", "HSAG:", "HLIG:"]
found = {}

print(f"Scanning {len(lines)} lines...")

current_code = None
for i, line in enumerate(lines):
    line_stripped = line.strip()
    # Check for Start
    for code in target_codes:
        if line.startswith(code):
            print(f"FOUND {code} at line {i+1}")
            found[code] = i+1
            current_code = code
    
    # Check for End (start of next section)
    # Assuming next section starts with uppercase letters and colon, no indent
    if current_code and i+1 > found[current_code] and line and not line.startswith(" ") and ":" in line:
        print(f"END OF {current_code} at line {i+1} (Next section: {line})")
        current_code = None
