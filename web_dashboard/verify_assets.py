import os
import re
from pathlib import Path

def verify_assets():
    """Verify that all assets referenced in templates exist in the static folder."""
    web_dashboard_dir = Path("web_dashboard")
    templates_dir = web_dashboard_dir / "templates"
    static_dir = web_dashboard_dir / "static"
    
    # Static URL path in app.py is /assets, mapping to web_dashboard/static
    # Also support /static/ just in case
    asset_patterns = [
        r'src=["\']/(assets|static)/(.*?)["\']',
        r'href=["\']/(assets|static)/(.*?)["\']'
    ]
    
    errors = 0
    checked = 0
    
    print(f"--- Verifying Assets in {templates_dir} ---")
    
    for template_file in templates_dir.glob("**/*.html"):
        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()
            
            for pattern in asset_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    prefix = match.group(1)
                    asset_path = match.group(2)
                    
                    # Clean up asset path (remove query params like ?v=123)
                    clean_asset_path = asset_path.split('?')[0]
                    
                    # Full local path
                    local_path = static_dir / clean_asset_path
                    
                    checked += 1
                    if not local_path.exists():
                        print(f"❌ MISSING ASSET in {template_file.name}:")
                        print(f"   Reference: /{prefix}/{asset_path}")
                        print(f"   Expected Location: {local_path}")
                        errors += 1
    
    print(f"\n--- Verification Complete ---")
    print(f"Checked: {checked}")
    print(f"Errors:  {errors}")
    
    # Also check Dockerfile.flask for missing copies
    dockerfile_path = web_dashboard_dir / "Dockerfile.flask"
    if dockerfile_path.exists():
        print(f"\n--- Checking {dockerfile_path.name} for JS copies ---")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            docker_content = f.read()
            
            # Check if we are copying the whole directory (the robust way)
            dir_copy_pattern = r'COPY --from=frontend-builder .*?static/js/ \./web_dashboard/static/js/'
            if re.search(dir_copy_pattern, docker_content):
                print(f"✅ Found directory-level COPY for static/js/ - All JS files included.")
            else:
                # Fall back to checking individual files
                js_files = list((static_dir / "js").glob("*.js"))
                for js_file in js_files:
                    if js_file.name not in docker_content and js_file.name != "types.js":
                        print(f"⚠️  {js_file.name} is in static/js but NOT explicitly copied in Dockerfile.flask!")
    
    return errors == 0

if __name__ == "__main__":
    if verify_assets():
        print("\n✅ All assets verified!")
        exit(0)
    else:
        print("\n❌ Asset verification failed!")
        exit(1)
