"""
Middleware for logging user actions in the DQX application.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app import crud
from app.database import get_db
import json


class UserActionLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log user actions for audit purposes."""
    
    # Actions that should be logged
    LOGGED_ACTIONS = {
        "POST": {
            "/login": {"action": "user_login", "resource_type": "auth"},
            "/logout": {"action": "user_logout", "resource_type": "auth"},
            "/register": {"action": "user_register", "resource_type": "auth"},
            "/editor/save": {"action": "script_create_update", "resource_type": "script"},
            "/editor/execute": {"action": "script_execute", "resource_type": "script"},
            "/schedules/": {"action": "schedule_create", "resource_type": "schedule"},
        },
        "GET": {
            "/editor/delete/": {"action": "script_delete", "resource_type": "script"},
            "/schedules/delete/": {"action": "schedule_delete", "resource_type": "schedule"},
            "/editor/{}/populate": {"action": "script_populate", "resource_type": "script"},
            "/editor/{}/publish": {"action": "script_publish", "resource_type": "script"},
        },
        "DELETE": {
            "/api/scripts/": {"action": "script_delete", "resource_type": "script"},
            "/api/schedules/": {"action": "schedule_delete", "resource_type": "schedule"},
        },
        "PUT": {
            "/api/scripts/": {"action": "script_update", "resource_type": "script"},
            "/api/schedules/": {"action": "schedule_update", "resource_type": "schedule"},
        }
    }
    
    async def dispatch(self, request: Request, call_next):
        # Continue with the request first
        response = await call_next(request)
        
        # Only log successful actions (2xx status codes)
        if 200 <= response.status_code < 300:
            self._log_action_if_needed(request, response)
        
        return response
    
    def _log_action_if_needed(self, request: Request, response):
        """Log the action if it matches our criteria."""
        try:
            # Get user from request state (set by UserMiddleware)
            user = getattr(request.state, 'user', None)
            if not user:
                return
            
            # Check if this action should be logged
            method = request.method
            path = request.url.path
            
            action_info = self._get_action_info(method, path)
            if not action_info:
                return
            
            # Extract resource ID from path if present
            resource_id = self._extract_resource_id(path)
            
            # Get client info
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")
            
            # Prepare details
            details = {
                "method": method,
                "path": path,
                "status_code": response.status_code
            }
            
            # Add form data for POST requests if available
            if method == "POST" and hasattr(request, '_json'):
                try:
                    details["request_data"] = request._json
                except Exception:
                    pass
            
            # Log the action
            db_gen = get_db()
            db = next(db_gen)
            try:
                result = crud.log_user_action(
                    db=db,
                    user_id=user.id,
                    username=user.username,
                    action=action_info["action"],
                    resource_type=action_info["resource_type"],
                    resource_id=resource_id,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                # Commit the transaction
                db.commit()
            except Exception as e:
                # Rollback on error
                db.rollback()
                print(f"Error logging user action: {e}")
            finally:
                db.close()
                
        except Exception as e:
            # Don't let logging errors affect the main request
            print(f"Error in UserActionLoggingMiddleware: {e}")
    
    def _get_action_info(self, method: str, path: str):
        """Get action info for the given method and path."""
        if method not in self.LOGGED_ACTIONS:
            return None
        
        method_actions = self.LOGGED_ACTIONS[method]
        
        # Exact match first
        if path in method_actions:
            return method_actions[path]
        
        # Pattern matching for paths with IDs
        for pattern, action_info in method_actions.items():
            if self._path_matches_pattern(path, pattern):
                return action_info
        
        return None
    
    def _path_matches_pattern(self, path: str, pattern: str):
        """Check if path matches a pattern with placeholders."""
        if "{}" not in pattern:
            return path.startswith(pattern)
        
        # Simple pattern matching for paths like /editor/{}/populate
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        
        if len(pattern_parts) != len(path_parts):
            return False
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part == "{}":
                continue  # Wildcard matches anything
            if pattern_part != path_part:
                return False
        
        return True
    
    def _extract_resource_id(self, path: str):
        """Extract resource ID from path."""
        import re
        # Look for numeric IDs in the path
        match = re.search(r'/(\d+)(?:/|$)', path)
        return int(match.group(1)) if match else None
    
    def _get_client_ip(self, request: Request):
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return None
