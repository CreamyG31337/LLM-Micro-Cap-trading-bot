#!/usr/bin/env python3
"""
Run trace specifically for Lance Colton
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

# Import the trace function
from trace_user_return import trace_user_return_calculation, SupabaseClient

client = SupabaseClient(use_service_role=True)

print("="*80)
print("TRACING LANCE COLTON'S RETURN CALCULATION")
print("="*80)

trace_user_return_calculation(client, "lance.colton@gmail.com", "Project Chimera")
