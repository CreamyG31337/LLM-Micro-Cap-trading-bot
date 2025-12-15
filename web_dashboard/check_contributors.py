
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Add parent directory to path to find web_dashboard modules
sys.path.append(str(Path.cwd()))
sys.path.append(str(Path.cwd() / "web_dashboard"))

load_dotenv()

from web_dashboard.supabase_client import SupabaseClient

def check_chimera_contributors():
    client = SupabaseClient()
    
    # Query all contributions for Project Chimera
    print("Querying fund_contributions for 'Project Chimera'...")
    response = client.supabase.table("fund_contributions").select("*").eq("fund", "Project Chimera").execute()
    
    if not response.data:
        print("No contributions found for Project Chimera.")
        return

    df = pd.DataFrame(response.data)
    
    # Filter for missing or empty emails
    missing_emails = df[df['email'].isnull() | (df['email'] == '')]
    
    if not missing_emails.empty:
        print(f"\nFound {len(missing_emails)} records with missing emails:")
        summary = missing_emails.groupby('contributor').size()
        print(summary)
        # Check if 'date' column exists, otherwise use 'timestamp'
        date_col = 'date' if 'date' in df.columns else 'timestamp'
        print("\nDetails:")
        print(missing_emails[['contributor', 'amount', 'contribution_type', date_col, 'email']].head())
    else:
        print("\nAll contributors for Project Chimera have emails.")

    # Also check the view
    print("\nQuerying contributor_ownership view...")
    view_response = client.supabase.table("contributor_ownership").select("*").eq("fund", "Project Chimera").execute()
    if view_response.data:
        view_df = pd.DataFrame(view_response.data)
        missing_emails_view = view_df[view_df['email'].isnull() | (view_df['email'] == '')]
        if not missing_emails_view.empty:
            print(f"\nFound {len(missing_emails_view)} contributors with missing emails in VIEW:")
            print(missing_emails_view[['contributor', 'net_contribution', 'email']])
        else:
            print("All contributors in VIEW have emails.")

if __name__ == "__main__":
    check_chimera_contributors()
