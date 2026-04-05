"""
Authentication endpoints.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.api import Token, UserLogin
from app.core.security import authenticate_user, create_access_token
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Authenticate user and return JWT token.
    
    DEMO MODE: Accepts any username/password for demonstration purposes.
    
    Args:
        credentials: Username and password
        
    Returns:
        JWT access token
    """
    # DEMO MODE: Accept any credentials
    # In production, use real authentication with authenticate_user()
    
    # Create a mock user from the provided username
    user_id = f"user-{hash(credentials.username) % 10000:04d}"
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": credentials.username,
            "user_id": user_id,
            "role": "provider"  # Default role for demo
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")
