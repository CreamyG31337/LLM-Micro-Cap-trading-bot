import os
import sys
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_dashboard'))

# Run the portfolio price update job for TODAY
from scheduler.jobs import update_portfolio_prices_job

print("=" * 60)
print("MANUALLY TRIGGERING PORTFOLIO PRICE UPDATE JOB")
print(f"Target date: {date.today()}")
print("=" * 60)

try:
    update_portfolio_prices_job(target_date=date.today())
    print("\n✅ Job completed")
except Exception as e:
    print(f"\n❌ Job failed: {e}")
    import traceback
    traceback.print_exc()
