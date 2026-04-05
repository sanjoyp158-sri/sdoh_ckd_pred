"""
Security utilities for authentication and authorization.
Minimal JWT-based authentication with RBAC.
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.api import TokenData, User


# HTTP Bearer token scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using SHA256 (minimal implementation)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with decoded information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username, user_id=user_id, role=role)
        return token_data
        
    except JWTError:
        raise credentials_exception


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        User object
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    # In a real implementation, fetch user from database
    # For minimal implementation, create user from token data
    user = User(
        user_id=token_data.user_id or "unknown",
        username=token_data.username or "unknown",
        role=token_data.role or "provider",
        active=True
    )
    
    return user


def require_role(allowed_roles: list):
    """
    Dependency to require specific roles (RBAC).
    
    Args:
        allowed_roles: List of allowed role names
        
    Returns:
        Dependency function
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return user
    
    return role_checker


# Mock user database for minimal implementation
# In production, this would be a real database with proper bcrypt hashing
# Using SHA256 for minimal implementation to avoid bcrypt compatibility issues
MOCK_USERS = {
    "provider1": {
        "user_id": "provider-001",
        "username": "provider1",
        "email": "provider1@hospital.com",
        # SHA256 hash of "password123"
        "hashed_password": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",
        "role": "provider",
        "active": True
    },
    "admin1": {
        "user_id": "admin-001",
        "username": "admin1",
        "email": "admin1@hospital.com",
        # SHA256 hash of "admin123"
        "hashed_password": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
        "role": "admin",
        "active": True
    }
}


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username
        password: Plain text password
        
    Returns:
        User object if authentication succeeds, None otherwise
    """
    user_dict = MOCK_USERS.get(username)
    if not user_dict:
        return None
    
    if not verify_password(password, user_dict["hashed_password"]):
        return None
    
    return User(
        user_id=user_dict["user_id"],
        username=user_dict["username"],
        email=user_dict.get("email"),
        role=user_dict["role"],
        active=user_dict["active"]
    )
