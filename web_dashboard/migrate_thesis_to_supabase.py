#!/usr/bin/env python3
"""
Migrate thesis data from YAML files to Supabase database.

This script reads existing thesis.yaml files from fund directories
and populates the Supabase fund_thesis and fund_thesis_pillars tables.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install supabase python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")
    
    return create_client(url, key)

def load_thesis_from_yaml(fund_dir: Path) -> Dict[str, Any]:
    """Load thesis data from YAML file."""
    thesis_file = fund_dir / "thesis.yaml"
    
    if not thesis_file.exists():
        print(f"⚠️  No thesis.yaml found in {fund_dir}")
        return None
    
    try:
        with open(thesis_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'guiding_thesis' not in data:
            print(f"❌ Invalid thesis structure in {thesis_file}")
            return None
        
        return data['guiding_thesis']
    except Exception as e:
        print(f"❌ Error loading thesis from {thesis_file}: {e}")
        return None

def migrate_thesis_to_supabase():
    """Migrate all thesis data to Supabase."""
    print("🔄 Starting thesis migration to Supabase...")
    
    try:
        supabase = get_supabase_client()
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        return False
    
    # Find all fund directories
    funds_dir = Path("trading_data/funds")
    if not funds_dir.exists():
        print(f"❌ Funds directory not found: {funds_dir}")
        return False
    
    migrated_count = 0
    error_count = 0
    
    for fund_dir in funds_dir.iterdir():
        if not fund_dir.is_dir():
            continue
        
        fund_name = fund_dir.name
        print(f"\n📁 Processing fund: {fund_name}")
        
        # Load thesis data from YAML
        thesis_data = load_thesis_from_yaml(fund_dir)
        if not thesis_data:
            print(f"⚠️  Skipping {fund_name} - no valid thesis data")
            continue
        
        try:
            # Insert or update thesis record
            thesis_record = {
                'fund': fund_name,
                'title': thesis_data.get('title', f"{fund_name} Investment Thesis"),
                'overview': thesis_data.get('overview', '')
            }
            
            # Check if thesis already exists
            existing = supabase.table('fund_thesis').select('id').eq('fund', fund_name).execute()
            
            if existing.data:
                # Update existing thesis
                thesis_id = existing.data[0]['id']
                supabase.table('fund_thesis').update(thesis_record).eq('id', thesis_id).execute()
                print(f"✅ Updated thesis for {fund_name}")
            else:
                # Insert new thesis
                result = supabase.table('fund_thesis').insert(thesis_record).execute()
                thesis_id = result.data[0]['id']
                print(f"✅ Created thesis for {fund_name}")
            
            # Delete existing pillars and insert new ones
            supabase.table('fund_thesis_pillars').delete().eq('thesis_id', thesis_id).execute()
            
            # Insert pillars
            pillars = thesis_data.get('pillars', [])
            if pillars:
                pillar_records = []
                for i, pillar in enumerate(pillars):
                    pillar_record = {
                        'thesis_id': thesis_id,
                        'name': pillar.get('name', ''),
                        'allocation': pillar.get('allocation', ''),
                        'thesis': pillar.get('thesis', ''),
                        'pillar_order': i
                    }
                    pillar_records.append(pillar_record)
                
                if pillar_records:
                    supabase.table('fund_thesis_pillars').insert(pillar_records).execute()
                    print(f"✅ Inserted {len(pillar_records)} pillars for {fund_name}")
            
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error migrating {fund_name}: {e}")
            error_count += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"✅ Successfully migrated: {migrated_count} funds")
    print(f"❌ Errors: {error_count} funds")
    
    return error_count == 0

def verify_migration():
    """Verify that thesis data was migrated correctly."""
    print("\n🔍 Verifying migration...")
    
    try:
        supabase = get_supabase_client()
        
        # Get all funds with thesis data
        result = supabase.table('fund_thesis').select('fund, title').execute()
        
        if not result.data:
            print("❌ No thesis data found in Supabase")
            return False
        
        print(f"✅ Found {len(result.data)} funds with thesis data:")
        for record in result.data:
            print(f"  - {record['fund']}: {record['title']}")
        
        # Test the get_fund_thesis function for each fund
        for record in result.data:
            fund_name = record['fund']
            try:
                # Use the SQL function to get complete thesis data
                result = supabase.rpc('get_fund_thesis', {'fund_name': fund_name}).execute()
                if result.data:
                    print(f"✅ Verified thesis data for {fund_name}")
                else:
                    print(f"⚠️  No thesis data returned for {fund_name}")
            except Exception as e:
                print(f"❌ Error verifying {fund_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Thesis Migration to Supabase")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("trading_data/funds").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Run migration
    success = migrate_thesis_to_supabase()
    
    if success:
        print("\n✅ Migration completed successfully!")
        
        # Verify migration
        if verify_migration():
            print("✅ Verification passed!")
        else:
            print("⚠️  Verification had issues - check the data manually")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
