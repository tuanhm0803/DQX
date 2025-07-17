"""
Middleware for user authentication and action logging in the DQX application.

This module contains all middleware classes for the DQX application:

1. UserMiddleware: Extracts user information from JWT tokens and stores it in request state
2. UserActionLoggingMiddleware: Logs user actions for audit and security purposes

The middleware are applied in the following order in main.py:
1. UserMiddleware (first - to have user available for other middleware)
2. UserActionLoggingMiddleware (second - to log actions with user context)
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app import crud
from app.database import get_db
import json


class UserMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and store user information in request state."""
    
    async def dispatch(self, request: Request, call_next):
        # Initialize user as None
        request.state.user = None
        
        try:
            # Extract and process user token
            self._process_user_token(request)
        except Exception as e:
            # Log any errors but continue processing
            print(f"Error in UserMiddleware: {e}")
            request.state.user = None
                
        # Always continue to the next handler
        response = await call_next(request)
        return response
    
    def _process_user_token(self, request: Request):
        """Extract and process user authentication token."""
        # Extract token from cookies
        access_token = request.cookies.get("access_token")
        if not access_token:
            return
            
        # Extract the token from the "Bearer <token>" format
        token = access_token[7:] if access_token.startswith("Bearer ") else access_token
        
        # Decode token and get user
        try:
            user = self._decode_token_and_get_user(token)
            request.state.user = user
        except Exception as e:
            print(f"Token processing error: {e}")
            request.state.user = None
    
    def _decode_token_and_get_user(self, token: str):
        """Decode JWT token and fetch user from database."""
        from jose import JWTError, jwt
        from app.auth import SECRET_KEY, ALGORITHM
        from app import crud
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return None
                
            return self._get_user_from_database(username)
        except JWTError:
            return None
    
    def _get_user_from_database(self, username: str):
        """Fetch user from database safely."""
        db_gen = None
        try:
            db_gen = get_db()
            conn = next(db_gen)
            return crud.get_user_by_username(conn, username)
        except Exception as db_error:
            print(f"Database error in UserMiddleware: {db_error}")
            return None
        finally:
            if db_gen:
                try:
                    db_gen.close()
                except Exception:
                    pass  # Ignore close errors


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
                crud.log_user_action(
                    db=db,
                    user_id=user.id,
                    username=user.username,
                    action=action_info["action"],
                    resource_type=action_info["resource_type"],
                    resource_id=resource_id,
                    details=details,
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
