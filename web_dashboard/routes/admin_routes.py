#!/usr/bin/env python3
"""
Admin Routes
============

Flask routes for admin user management, contributors, and contributor access.
Migrated from app.py to follow the blueprint pattern.
"""

from flask import Blueprint, render_template, request, jsonify
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path to allow importing from root
sys.path.append(str(Path(__file__).parent.parent))

from auth import require_admin
from supabase_client import SupabaseClient
from flask_cache_utils import cache_data
from app import get_navigation_context, get_supabase_client
from flask_cache_utils import cache_data
import time
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Cached log helper
@cache_data(ttl=5)
def _get_cached_application_logs(level_filter, search, exclude_modules):
    """Get application logs with caching (5s TTL for near real-time)"""
    from log_handler import read_logs_from_file
    
    try:
        # Get all filtered logs
        all_logs = read_logs_from_file(
            n=None,
            level=level_filter,
            search=search if search else None,
            return_all=True,
            exclude_modules=exclude_modules if exclude_modules else None
        )
        
        # Convert datetime objects to strings for cache compatibility
        serializable_logs = []
        for log in all_logs:
            serializable_log = log.copy()
            if 'timestamp' in serializable_log and hasattr(serializable_log['timestamp'], 'strftime'):
                serializable_log['timestamp'] = serializable_log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            serializable_logs.append(serializable_log)
        
        # Reverse for newest first
        return list(reversed(serializable_logs))
    except Exception as e:
        logger.error(f"Error in _get_cached_application_logs: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@cache_data(ttl=5)
def _get_cached_ollama_log_lines():
    """Get Ollama log lines with caching"""
    from pathlib import Path
    
    log_file = Path(__file__).parent.parent / 'logs' / 'ollama.log'
    
    if not log_file.exists():
        return []
    
    try:
        # Read up to 5MB from end for efficiency
        file_size = log_file.stat().st_size
        if file_size == 0:
            return []
        
        buffer_size = min(5 * 1024 * 1024, file_size)
        with open(log_file, 'rb') as f:
            f.seek(max(0, file_size - buffer_size))
            buffer = f.read().decode('utf-8', errors='ignore')
        
        lines = buffer.split('\n')
        if file_size > buffer_size:
            lines = lines[1:]  # Skip first partial line
        
        # Reverse for newest first
        return list(reversed(lines))
    except Exception as e:
        logger.error(f"Error reading Ollama log file: {e}")
        return []

admin_bp = Blueprint('admin', __name__)

# Cached helper functions
@cache_data(ttl=60)
def _get_cached_users_flask():
    """Get all users with their fund assignments (cached for 60s)"""
    try:
        # Use service_role to bypass RLS for admin operations
        client = SupabaseClient(use_service_role=True)
        
        result = client.supabase.rpc('list_users_with_funds').execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Error in _get_cached_users_flask: {e}", exc_info=True)
        return []

@cache_data(ttl=60)
def _get_cached_contributors_flask():
    """Get all contributors (cached for 60s)"""
    try:
        # Use service_role to bypass RLS for admin operations
        client = SupabaseClient(use_service_role=True)
        
        result = client.supabase.table("contributors").select("id, name, email").order("name").execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Error getting contributors: {e}", exc_info=True)
        return []

# Page route
@admin_bp.route('/v2/admin/users')
@require_admin
def users_page():
    """Admin user & access management page (Flask v2)"""
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_theme
        
        user_email = get_user_email_flask()
        user_theme = get_user_theme() or 'system'
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='admin_users')
        
        logger.debug(f"Rendering users page for user: {user_email}")
        
        return render_template('users.html', 
                             user_email=user_email,
                             user_theme=user_theme,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error rendering users page: {e}", exc_info=True)
        user_theme = 'system'
        nav_context = get_navigation_context(current_page='admin_users')
        return render_template('users.html', 
                             user_email='Admin',
                             user_theme=user_theme,
                             **nav_context)

# User management routes
@admin_bp.route('/api/admin/users/list')
@require_admin
def api_admin_users_list():
    """Get all users with their fund assignments (for Flask page)"""
    try:
        users = _get_cached_users_flask()
        
        # Get stats
        stats = {
            "total_users": len(users),
            "total_funds": len(set(fund for user in users for fund in (user.get('funds') or []))),
            "total_assignments": sum(len(user.get('funds') or []) for user in users)
        }
        
        return jsonify({"users": users, "stats": stats})
    except Exception as e:
        logger.error(f"Error in api_admin_users_list: {e}", exc_info=True)
        return jsonify({"error": "Failed to load users", "users": [], "stats": {"total_users": 0, "total_funds": 0, "total_assignments": 0}}), 500

@admin_bp.route('/api/admin/users/grant-admin', methods=['POST'])
@require_admin
def api_admin_grant_admin():
    """Grant admin role to a user"""
    try:
        from flask_auth_utils import can_modify_data_flask
        if not can_modify_data_flask():
            return jsonify({"error": "Read-only admin cannot modify user roles"}), 403
        
        data = request.get_json()
        user_email = data.get('user_email')
        
        if not user_email:
            return jsonify({"error": "User email required"}), 400
        
        import requests
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/grant_admin_role",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json={"user_email": user_email}
        )
        
        if response.status_code == 200:
            result_data = response.json()
            if isinstance(result_data, list) and len(result_data) > 0:
                result_data = result_data[0]
            
            if result_data and result_data.get('success'):
                # Clear cache
                _get_cached_users_flask.clear_all_cache()
                return jsonify(result_data), 200
            else:
                return jsonify(result_data or {"error": "Failed to grant admin role"}), 400
        else:
            error_msg = response.json().get('message', 'Failed to grant admin role') if response.text else 'Failed to grant admin role'
            return jsonify({"error": error_msg}), 400
    except Exception as e:
        logger.error(f"Error granting admin role: {e}", exc_info=True)
        return jsonify({"error": "Failed to grant admin role"}), 500

@admin_bp.route('/api/admin/users/revoke-admin', methods=['POST'])
@require_admin
def api_admin_revoke_admin():
    """Revoke admin role from a user"""
    try:
        from flask_auth_utils import can_modify_data_flask
        if not can_modify_data_flask():
            return jsonify({"error": "Read-only admin cannot modify user roles"}), 403
        
        data = request.get_json()
        user_email = data.get('user_email')
        
        if not user_email:
            return jsonify({"error": "User email required"}), 400
        
        import requests
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/revoke_admin_role",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json={"user_email": user_email}
        )
        
        if response.status_code == 200:
            result_data = response.json()
            if isinstance(result_data, list) and len(result_data) > 0:
                result_data = result_data[0]
            
            if result_data and result_data.get('success'):
                # Clear cache
                _get_cached_users_flask.clear_all_cache()
                return jsonify(result_data), 200
            else:
                return jsonify(result_data or {"error": "Failed to revoke admin role"}), 400
        else:
            error_msg = response.json().get('message', 'Failed to revoke admin role') if response.text else 'Failed to revoke admin role'
            return jsonify({"error": error_msg}), 400
    except Exception as e:
        logger.error(f"Error revoking admin role: {e}", exc_info=True)
        return jsonify({"error": "Failed to revoke admin role"}), 500

@admin_bp.route('/api/admin/users/delete', methods=['POST'])
@require_admin
def api_admin_delete_user():
    """Delete a user safely"""
    try:
        from flask_auth_utils import can_modify_data_flask
        if not can_modify_data_flask():
            return jsonify({"error": "Read-only admin cannot delete users"}), 403
        
        data = request.get_json()
        user_email = data.get('user_email')
        
        if not user_email:
            return jsonify({"error": "User email required"}), 400
        
        import requests
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/delete_user_safe",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json={"user_email": user_email}
        )
        
        if response.status_code == 200:
            result_data = response.json()
            if result_data and result_data.get('success'):
                # Clear cache
                _get_cached_users_flask.clear_all_cache()
                return jsonify(result_data), 200
            else:
                return jsonify(result_data or {"error": "Failed to delete user"}), 400
        else:
            error_msg = response.json().get('message', 'Failed to delete user') if response.text else 'Failed to delete user'
            return jsonify({"error": error_msg}), 400
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete user"}), 500

@admin_bp.route('/api/admin/users/send-invite', methods=['POST'])
@require_admin
def api_admin_send_invite():
    """Send magic link invite to a user"""
    try:
        from flask_auth_utils import can_modify_data_flask, get_user_email_flask
        data = request.get_json()
        user_email = data.get('user_email')
        
        if not user_email:
            return jsonify({"error": "User email required"}), 400
        
        # Allow readonly_admin to send invite to themselves
        current_email = get_user_email_flask()
        can_send = can_modify_data_flask() or (user_email == current_email)
        
        if not can_send:
            return jsonify({"error": "Read-only admin can only send invites to themselves"}), 403
        
        # Use Supabase client to send magic link
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
        
        if not supabase_url or not publishable_key:
            return jsonify({"error": "Supabase configuration missing"}), 500
        
        app_domain = os.getenv("APP_DOMAIN")
        if not app_domain:
            return jsonify({"error": "APP_DOMAIN environment variable is required"}), 500
        
        redirect_url = os.getenv("MAGIC_LINK_REDIRECT_URL", f"https://{app_domain}/auth_callback.html")
        
        supabase = create_client(supabase_url, publishable_key)
        response = supabase.auth.sign_in_with_otp({
            "email": user_email,
            "options": {
                "email_redirect_to": redirect_url
            }
        })
        
        if response:
            return jsonify({"success": True, "message": "Invite sent to your email"}), 200
        else:
            return jsonify({"error": "Failed to send invite"}), 500
    except Exception as e:
        logger.error(f"Error sending invite: {e}", exc_info=True)
        return jsonify({"error": f"Failed to send invite: {str(e)}"}), 500

@admin_bp.route('/api/admin/users/update-contributor-email', methods=['POST'])
@require_admin
def api_admin_update_contributor_email():
    """Update contributor email address"""
    try:
        from flask_auth_utils import can_modify_data_flask
        if not can_modify_data_flask():
            return jsonify({"error": "Read-only admin cannot update contributor emails"}), 403
        
        data = request.get_json()
        contributor_name = data.get('contributor_name')
        contributor_id = data.get('contributor_id')
        contributor_type = data.get('contributor_type')  # 'contributor', 'fund_contribution', 'user'
        new_email = data.get('new_email')
        
        if not new_email:
            return jsonify({"error": "New email address required"}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, new_email):
            return jsonify({"error": "Invalid email format"}), 400
        
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        updates_made = []
        
        # Update based on type
        if contributor_type == 'contributor' and contributor_id:
            try:
                client.supabase.table("contributors").update(
                    {"email": new_email}
                ).eq("id", contributor_id).execute()
                updates_made.append("contributors table")
            except Exception as e:
                logger.warning(f"Could not update contributors table: {e}")
        
        # Always update fund_contributions for this contributor name
        try:
            client.supabase.table("fund_contributions").update(
                {"email": new_email}
            ).eq("contributor", contributor_name).execute()
            updates_made.append("fund_contributions records")
        except Exception as e:
            logger.warning(f"Could not update fund_contributions: {e}")
        
        # If it's a registered user, also update auth
        if contributor_type == 'user' and contributor_id:
            try:
                from supabase import create_client
                supabase_url = os.getenv("SUPABASE_URL")
                service_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                
                if supabase_url and service_key:
                    admin_client = create_client(supabase_url, service_key)
                    
                    # Check if email already exists
                    users_response = admin_client.auth.admin.list_users()
                    users_list = users_response if isinstance(users_response, list) else getattr(users_response, 'users', [])
                    
                    email_exists = False
                    for u in users_list:
                        check_email = u.email if hasattr(u, 'email') else u.get('email') if isinstance(u, dict) else None
                        if check_email and check_email.lower() == new_email.lower():
                            check_id = u.id if hasattr(u, 'id') else u.get('id') if isinstance(u, dict) else None
                            if str(check_id) != str(contributor_id):
                                email_exists = True
                                break
                    
                    if email_exists:
                        return jsonify({"error": f"Email {new_email} is already in use by another user"}), 400
                    
                    # Update email in auth.users
                    update_response = admin_client.auth.admin.update_user_by_id(
                        contributor_id,
                        {"email": new_email}
                    )
                    
                    if update_response and update_response.user:
                        updates_made.append("auth.users")
                        
                        # Also update email in user_profiles table
                        try:
                            client.supabase.table("user_profiles").update(
                                {"email": new_email}
                            ).eq("user_id", contributor_id).execute()
                            updates_made.append("user_profiles")
                        except Exception as profile_error:
                            logger.warning(f"Could not update user_profiles: {profile_error}")
                    else:
                        return jsonify({"error": "Failed to update email in auth.users"}), 500
            except Exception as auth_error:
                logger.warning(f"Could not update auth.users: {auth_error}")
        
        if updates_made:
            # Clear caches
            _get_cached_users_flask.clear_all_cache()
            _get_cached_contributors_flask.clear_all_cache()
            return jsonify({
                "success": True,
                "message": f"Email updated in: {', '.join(updates_made)}",
                "updates_made": updates_made
            }), 200
        else:
            return jsonify({"error": "No updates were made"}), 400
    except Exception as e:
        logger.error(f"Error updating contributor email: {e}", exc_info=True)
        return jsonify({"error": f"Failed to update email: {str(e)}"}), 500

# Contributor routes
@admin_bp.route('/api/admin/contributors')
@require_admin
def api_admin_contributors():
    """Get all contributors"""
    try:
        contributors = _get_cached_contributors_flask()
        return jsonify({"contributors": contributors})
    except Exception as e:
        logger.error(f"Error getting contributors: {e}", exc_info=True)
        return jsonify({"error": "Failed to load contributors", "contributors": []}), 500

@admin_bp.route('/api/admin/contributors/unregistered')
@require_admin
def api_admin_unregistered_contributors():
    """Get unregistered contributors"""
    try:
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Failed to connect to database", "contributors": []}), 500
        
        result = client.supabase.rpc('list_unregistered_contributors').execute()
        contributors = result.data if result.data else []
        return jsonify({"contributors": contributors})
    except Exception as e:
        logger.error(f"Error getting unregistered contributors: {e}", exc_info=True)
        # Check if it's a missing table error
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str or "42p01" in error_str:
            return jsonify({
                "error": "Contributors table not found. Run migration DF_009 first.",
                "contributors": []
            }), 404
        return jsonify({"error": f"Failed to load unregistered contributors: {str(e)}", "contributors": []}), 500

# Contributor access routes
@admin_bp.route('/api/admin/contributor-access')
@require_admin
def api_admin_contributor_access():
    """Get all contributor access records"""
    try:
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Failed to connect to database", "access": []}), 500
        
        # Get access records
        access_result = client.supabase.table("contributor_access").select(
            "id, contributor_id, user_id, access_level, granted_at"
        ).execute()
        
        if not access_result.data:
            return jsonify({"access": []})
        
        # Get contributor and user details
        contributors = _get_cached_contributors_flask()
        users = _get_cached_users_flask()
        
        access_list = []
        for access in access_result.data:
            # Get contributor details
            contrib = next((c for c in contributors if c['id'] == access['contributor_id']), {})
            # Get user details
            user = next((u for u in users if u.get('user_id') == access['user_id']), {})
            
            access_list.append({
                "id": access['id'],
                "contributor": contrib.get('name', 'Unknown'),
                "contributor_email": contrib.get('email', 'No email'),
                "user_email": user.get('email', 'Unknown'),
                "user_name": user.get('full_name', ''),
                "access_level": access.get('access_level', 'viewer'),
                "granted": access.get('granted_at', '')[:10] if access.get('granted_at') else ''
            })
        
        return jsonify({"access": access_list})
    except Exception as e:
        logger.error(f"Error getting contributor access: {e}", exc_info=True)
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str or "42p01" in error_str:
            return jsonify({
                "error": "Contributor access table not found. Run migration DF_009 first.",
                "access": []
            }), 404
        return jsonify({"error": f"Failed to load access records: {str(e)}", "access": []}), 500

@admin_bp.route('/api/admin/contributor-access/grant', methods=['POST'])
@require_admin
def api_admin_grant_contributor_access():
    """Grant contributor access to a user"""
    try:
        data = request.get_json()
        contributor_email = data.get('contributor_email')
        user_email = data.get('user_email')
        access_level = data.get('access_level', 'viewer')
        
        if not contributor_email or not user_email:
            return jsonify({"error": "Contributor email and user email required"}), 400
        
        if access_level not in ['viewer', 'manager', 'owner']:
            return jsonify({"error": "Invalid access level. Must be viewer, manager, or owner"}), 400
        
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        result = client.supabase.rpc(
            'grant_contributor_access',
            {
                'contributor_email': contributor_email,
                'user_email': user_email,
                'access_level': access_level
            }
        ).execute()
        
        if result.data:
            result_data = result.data[0] if isinstance(result.data, list) else result.data
            if result_data.get('success'):
                # Clear cache
                _get_cached_contributors_flask.clear_all_cache()
                return jsonify(result_data), 200
            else:
                return jsonify(result_data), 400
        else:
            return jsonify({"error": "Failed to grant access"}), 500
    except Exception as e:
        logger.error(f"Error granting contributor access: {e}", exc_info=True)
        return jsonify({"error": f"Failed to grant access: {str(e)}"}), 500

@admin_bp.route('/v2/admin/system')
@require_admin
def system_page():
    """System Monitoring Page"""
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_theme
        
        user_email = get_user_email_flask()
        user_theme = get_user_theme() or 'system'
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='admin_system')
        
        return render_template('system.html', 
                             user_email=user_email,
                             user_theme=user_theme,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error rendering system page: {e}", exc_info=True)
        return render_template('error.html', error=str(e))

@admin_bp.route('/api/admin/system/status')
@require_admin
def api_system_status():
    """Get overall system status"""
    try:
        from admin_utils import get_system_status_cached
        
        # Get cached system stats
        status = get_system_status_cached()
        
        # Get recent job logs
        recent_jobs = []
        try:
            from scheduler.scheduler_core import get_job_logs
            # List of key jobs to monitor
            jobs_to_check = ['exchange_rates', 'portfolio_update', 'social_sentiment']
            
            for job_id in jobs_to_check:
                try:
                    logs = get_job_logs(job_id, limit=1)
                    if logs:
                        log = logs[0]
                        recent_jobs.append({
                            'job_id': job_id,
                            'success': log['success'],
                            'message': log['message'],
                            'timestamp': log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        })
                except Exception:
                    pass
        except ImportError:
            pass
            
        return jsonify({
            "status": status,
            "jobs": recent_jobs
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/admin/system/logs/application')
@require_admin
def api_logs_application():
    """Get application logs"""
    try:
        level = request.args.get('level', 'INFO + ERROR')
        limit = int(request.args.get('limit', 100))
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        
        # Handle "INFO + ERROR" logic
        if level == "INFO + ERROR":
            level_filter = ["INFO", "ERROR"]
        elif level == "All":
            level_filter = None
        else:
            level_filter = level
            
        exclude_heartbeat = request.args.get('exclude_heartbeat', 'true').lower() == 'true'
        exclude_modules = ['scheduler.scheduler_core.heartbeat'] if exclude_heartbeat else None
        
        all_logs = _get_cached_application_logs(level_filter, search, exclude_modules)
        
        # Pagination
        total = len(all_logs)
        start = (page - 1) * limit
        end = start + limit
        logs = all_logs[start:end]
        
        return jsonify({
            'logs': logs,
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit if total > 0 else 1
        })
    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/admin/system/docker/containers')
@require_admin
def api_docker_containers():
    """List running docker containers"""
    if not os.path.exists("/var/run/docker.sock") and os.name != 'nt': # Minimal check
         # On Windows it might be different, typically npipe:////./pipe/docker_engine
         pass 

    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list(all=True)
        
        results = []
        for c in containers:
            results.append({
                'id': c.id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else 'unknown'
            })
            
        # Sort Ollama first
        results.sort(key=lambda x: (0 if 'ollama' in x['name'].lower() else 1, x['name']))
        
        return jsonify({"containers": results})
    except ImportError:
        return jsonify({"error": "Docker python library not installed"}), 500
    except Exception as e:
        logger.warning(f"Docker error: {e}")
        return jsonify({"error": f"Docker error: {str(e)}"}), 500

@admin_bp.route('/api/admin/system/docker/logs/<container_id>')
@require_admin
def api_docker_logs(container_id):
    """Get logs for a specific container"""
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_id)
        
        tail = int(request.args.get('tail', 500))
        logs = container.logs(tail=tail).decode('utf-8', errors='replace')
        
        # Split and reverse (newest first)
        lines = logs.split('\n')
        lines.reverse()
        
        return jsonify({
            "logs": "\n".join(lines[:2000]), # Limit return size
            "name": container.name
        })
    except Exception as e:
        logger.error(f"Error fetching docker logs: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/admin/system/files')
@require_admin
def api_list_log_files():
    """List available log files"""
    try:
        log_dir = Path(__file__).parent.parent / 'logs'
        if not log_dir.exists():
             return jsonify({"files": []})
             
        files = []
        for f in log_dir.rglob("*.log"):
             files.append(str(f.relative_to(log_dir)))
        for f in log_dir.rglob("*.txt"):
             files.append(str(f.relative_to(log_dir)))
             
        return jsonify({"files": sorted(files)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/admin/system/files/content')
@require_admin
def api_read_log_file():
    """Read content of a log file"""
    try:
        filename = request.args.get('filename')
        if not filename:
            return jsonify({"error": "Filename required"}), 400
            
        # Security check - ensure no path traversal
        if '..' in filename or filename.startswith('/'):
             return jsonify({"error": "Invalid filename"}), 400
             
        log_dir = Path(__file__).parent.parent / 'logs'
        file_path = log_dir / filename
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
            
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Read last 2000 lines approx
             lines = f.readlines()
             content = "".join(reversed(lines[-2000:]))
             
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

