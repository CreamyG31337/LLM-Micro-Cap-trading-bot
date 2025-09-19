#!/usr/bin/env python3
"""
Authentication system for portfolio dashboard
Handles user login, registration, and fund access control
"""

import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for
import requests
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    """Handles user authentication and authorization"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-this")
        
    def get_user_funds(self, user_id: str) -> List[str]:
        """Get funds assigned to a user"""
        try:
            # Get user's assigned funds from Supabase
            response = requests.post(
                f"{self.supabase_url}/rest/v1/rpc/get_user_funds",
                headers={
                    "apikey": self.supabase_anon_key,
                    "Authorization": f"Bearer {self.supabase_anon_key}",
                    "Content-Type": "application/json"
                },
                json={"user_uuid": user_id}
            )
            
            if response.status_code == 200:
                funds = [row["fund_name"] for row in response.json()]
                return funds
            else:
                logger.error(f"Error getting user funds: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting user funds: {e}")
            return []
    
    def check_fund_access(self, user_id: str, fund_name: str) -> bool:
        """Check if user has access to a specific fund"""
        try:
            response = requests.post(
                f"{self.supabase_url}/rest/v1/rpc/user_has_fund_access",
                headers={
                    "apikey": self.supabase_anon_key,
                    "Authorization": f"Bearer {self.supabase_anon_key}",
                    "Content-Type": "application/json"
                },
                json={"user_uuid": user_id, "fund_name": fund_name}
            )
            
            if response.status_code == 200:
                return response.json()
            return False
        except Exception as e:
            logger.error(f"Error checking fund access: {e}")
            return False
    
    def create_user_session(self, user_id: str, email: str) -> str:
        """Create a JWT session token for the user"""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def verify_session(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT session token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

# Global auth manager instance
auth_manager = AuthManager()

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for session token in cookies or headers
        token = request.cookies.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        
        user_data = auth_manager.verify_session(token)
        if not user_data:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Add user data to request context
        request.user_id = user_data["user_id"]
        request.user_email = user_data["email"]
        
        return f(*args, **kwargs)
    return decorated_function

def require_fund_access(fund_name: str):
    """Decorator to require access to a specific fund"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user_id'):
                return jsonify({"error": "Authentication required"}), 401
            
            if not auth_manager.check_fund_access(request.user_id, fund_name):
                return jsonify({"error": "Access denied to this fund"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_funds():
    """Get funds for the current user"""
    if not hasattr(request, 'user_id'):
        return []
    return auth_manager.get_user_funds(request.user_id)
