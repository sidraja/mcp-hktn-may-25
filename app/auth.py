"""
Authentication module for the Trino MCP client.

This module provides authentication handlers for:
- No authentication (development mode)
- Basic authentication
- JWT token authentication
"""
import os
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
import base64
import json
import hashlib
import hmac

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from .errors import TrinoAuthError

logger = logging.getLogger(__name__)

# Configuration from environment variables
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "60"))

# Basic auth credentials - these would typically come from a database or config file
# For simplicity, we're using environment variables
BASIC_AUTH_USERS = {}
BASIC_AUTH_USERS_STR = os.environ.get("BASIC_AUTH_USERS", "")
if BASIC_AUTH_USERS_STR:
    # Format: "username1:password1,username2:password2"
    for user_pass in BASIC_AUTH_USERS_STR.split(","):
        parts = user_pass.strip().split(":")
        if len(parts) == 2:
            BASIC_AUTH_USERS[parts[0]] = parts[1]

# Flag to enable/disable authentication
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").lower() == "true"

# Auth mode: none, basic, jwt, or all
AUTH_MODE = os.environ.get("AUTH_MODE", "none").lower()

# Security schemes
basic_security = HTTPBasic(auto_error=False)
bearer_security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class TokenData(BaseModel):
    """Data model for JWT token claims."""
    username: str
    scopes: List[str] = []
    exp: Optional[int] = None


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    return AUTH_ENABLED


def get_auth_mode() -> str:
    """Get the current authentication mode."""
    return AUTH_MODE


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed version.
    
    In a production environment, you would use a proper password hashing
    algorithm like bcrypt, but for simplicity we're using a simple comparison.
    """
    # In a real implementation, use a proper password hashing library:
    # from passlib.context import CryptContext
    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # return pwd_context.verify(plain_password, hashed_password)
    
    # Simple implementation for demo purposes
    return plain_password == hashed_password


def get_password_hash(password: str) -> str:
    """
    Hash a password for storage.
    
    In a production environment, you would use a proper password hashing
    algorithm like bcrypt, but for simplicity we're using a simple string.
    """
    # In a real implementation, use a proper password hashing library:
    # from passlib.context import CryptContext
    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # return pwd_context.hash(password)
    
    # Simple implementation for demo purposes
    return password


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate a user with username and password.
    
    Args:
        username: The username to authenticate
        password: The password to verify
        
    Returns:
        True if authentication succeeds, False otherwise
    """
    if username not in BASIC_AUTH_USERS:
        return False
    
    stored_password = BASIC_AUTH_USERS[username]
    return verify_password(password, stored_password)


def create_jwt_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with the given data.
    
    Args:
        data: Data to include in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    
    to_encode.update({"exp": expire.timestamp()})
    
    # In a real implementation, use a proper JWT library:
    # import jwt
    # encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # Simple implementation for demo purposes
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_bytes = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
    payload_bytes = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).rstrip(b"=")
    
    message = header_bytes + b"." + payload_bytes
    signature = hmac.new(JWT_SECRET_KEY.encode(), message, hashlib.sha256).digest()
    signature_bytes = base64.urlsafe_b64encode(signature).rstrip(b"=")
    
    encoded_jwt = (header_bytes + b"." + payload_bytes + b"." + signature_bytes).decode()
    
    return encoded_jwt


def decode_jwt_token(token: str) -> TokenData:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        TokenData object with the decoded claims
        
    Raises:
        HTTPException: If the token is invalid, expired, or has an invalid signature
    """
    # In a real implementation, use a proper JWT library:
    # import jwt
    # try:
    #     payload = jwt.decode(
    #         token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
    #     )
    #     username = payload.get("sub")
    #     exp = payload.get("exp")
    #     scopes = payload.get("scopes", [])
    #     
    #     if username is None:
    #         raise HTTPException(
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #             detail="Invalid authentication credentials",
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )
    #         
    #     return TokenData(username=username, scopes=scopes, exp=exp)
    # except jwt.JWTError:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid authentication credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    
    # Simple implementation for demo purposes
    try:
        # Split the token into header, payload, and signature
        header_b64, payload_b64, signature_b64 = token.split(".")
        
        # Decode the payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)).decode()
        payload = json.loads(payload_json)
        
        # Verify the token hasn't expired
        exp = payload.get("exp")
        if exp and exp < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username = payload.get("sub")
        scopes = payload.get("scopes", [])
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify the signature
        message = (header_b64 + "." + payload_b64).encode()
        expected_signature = hmac.new(JWT_SECRET_KEY.encode(), message, hashlib.sha256).digest()
        actual_signature = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(username=username, scopes=scopes, exp=exp)
        
    except Exception as e:
        logger.error(f"Error decoding JWT token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    basic_credentials: Optional[HTTPBasicCredentials] = Depends(basic_security),
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[str]:
    """
    Get the current user from various authentication methods.
    This is the dependency to use when authentication is optional.
    
    Args:
        basic_credentials: Optional HTTP Basic Auth credentials
        bearer_credentials: Optional Bearer token credentials
        api_key: Optional API key
        
    Returns:
        Username if authentication is successful, None otherwise
    """
    # If authentication is disabled, return None
    if not is_auth_enabled():
        return None
    
    # Check auth mode and use appropriate method
    auth_mode = get_auth_mode()
    
    # If auth mode is none, return None
    if auth_mode == "none":
        return None
    
    # Try bearer token auth if applicable
    if (auth_mode == "bearer" or auth_mode == "all") and bearer_credentials:
        try:
            token_data = decode_jwt_token(bearer_credentials.credentials)
            return token_data.username
        except HTTPException:
            pass
    
    # Try basic auth if applicable
    if (auth_mode == "basic" or auth_mode == "all") and basic_credentials:
        username = basic_credentials.username
        password = basic_credentials.password
        
        if authenticate_user(username, password):
            return username
    
    # If we got here and auth is required, authentication failed
    return None


async def get_current_user(
    basic_credentials: Optional[HTTPBasicCredentials] = Depends(basic_security),
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    api_key: Optional[str] = Depends(api_key_header),
) -> str:
    """
    Get the current user from various authentication methods.
    This is the dependency to use when authentication is required.
    
    Args:
        basic_credentials: Optional HTTP Basic Auth credentials
        bearer_credentials: Optional Bearer token credentials
        api_key: Optional API key
        
    Returns:
        Username if authentication is successful
        
    Raises:
        HTTPException: If authentication fails
    """
    # If authentication is disabled, return a default user
    if not is_auth_enabled():
        return "anonymous"
    
    username = await get_current_user_optional(basic_credentials, bearer_credentials, api_key)
    
    if username:
        return username
    
    # If we got here, authentication failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": 'Basic realm="MCP API", Bearer'},
    )


def get_trino_auth_headers(username: str) -> Dict[str, str]:
    """
    Get Trino authentication headers for the given username.
    
    Args:
        username: The authenticated username
        
    Returns:
        Dictionary of headers to add to Trino requests
    """
    # In a real implementation, you might have mapping of users to Trino credentials
    # or use a pass-through mechanism
    
    # Simple implementation for demo purposes
    return {
        "X-Trino-User": username
    } 