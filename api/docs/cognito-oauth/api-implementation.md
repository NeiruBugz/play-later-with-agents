# API Implementation - FastAPI Backend

## Overview

This document covers the FastAPI backend implementation for the Backend Proxy Pattern approach. The backend handles all OAuth complexity, token management, and session storage while providing HTTPOnly cookies to the frontend.

## Implementation Architecture

```
Frontend Request → Backend OAuth Handlers → Cognito API → Session Storage → HTTPOnly Cookie Response
```

## Core Components

### 1. Authentication Router
### 2. Session Management
### 3. Token Security
### 4. Local Development Configuration

## Complete Backend Implementation

Following your project's architecture pattern of thin routes with service layer separation:

### Service Layer Structure
```
app/
├── routers/
│   └── auth.py          # Thin HTTP routes
├── services/
│   └── auth_service.py  # Business logic
├── core/
│   ├── session.py       # Session management
│   └── crypto.py        # Security utilities
└── schemas/
    └── auth.py          # Request/response models
```

### Authentication Service (app/services/auth_service.py)

```python
# app/services/auth_service.py
"""
Authentication service implementing OAuth flow with Cognito.
Contains all business logic for authentication operations.
"""
import secrets
import httpx
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.core.config import settings
from app.core.session import session_store
from app.core.crypto import encrypt_token, hash_token
from app.schemas.auth import UserInfo, TokenData

@dataclass(frozen=True)
class AuthResult:
    success: bool
    session_id: Optional[str] = None
    error_message: Optional[str] = None
    redirect_url: Optional[str] = None

@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    session_id: str

class AuthService:
    """Service for handling OAuth authentication with AWS Cognito."""
    
    @staticmethod
    async def initiate_login(client_ip: str) -> Tuple[str, str]:
        """
        Initiate OAuth login flow.
        
        Returns:
            Tuple of (cognito_url, state) for redirect and tracking
        """
        # Generate secure state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state temporarily (5 min expiration)
        await session_store.store_temp_state(
            state=state,
            client_ip=client_ip,
            expires_in=300  # 5 minutes
        )
        
        # Build Cognito login URL
        cognito_url = (
            f"https://{settings.cognito_domain}/login?"
            f"client_id={settings.cognito_client_id}&"
            f"response_type=code&"
            f"scope=openid+email+profile&"
            f"redirect_uri={settings.api_callback_url}&"
            f"state={state}&"
            f"identity_provider=Google"  # Force Google login
        )
        
        return cognito_url, state
    
    @staticmethod
    async def handle_oauth_callback(
        code: str, 
        state: str, 
        client_ip: str
    ) -> AuthResult:
        """
        Handle OAuth callback and create session.
        
        Args:
            code: Authorization code from Cognito
            state: State parameter for CSRF protection
            client_ip: Client IP for state verification
            
        Returns:
            AuthResult with session info or error
        """
        try:
            # Verify state parameter (CSRF protection)
            if not await session_store.verify_temp_state(state, client_ip):
                return AuthResult(
                    success=False,
                    error_message="Invalid state parameter",
                    redirect_url=f"{settings.frontend_url}/auth/error?reason=invalid_state"
                )
            
            # Exchange authorization code for tokens
            tokens = await AuthService._exchange_code_for_tokens(code)
            
            # Decode and validate ID token
            user_info = await AuthService._decode_and_validate_id_token(tokens["id_token"])
            
            # Create secure session
            session_id = await AuthService._create_user_session(
                user_info=user_info,
                tokens=tokens
            )
            
            # Clean up temporary state
            await session_store.delete_temp_state(state)
            
            return AuthResult(
                success=True,
                session_id=session_id,
                redirect_url=f"{settings.frontend_url}/dashboard"
            )
            
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=str(e),
                redirect_url=f"{settings.frontend_url}/auth/error?reason=oauth_failed"
            )
    
    @staticmethod
    async def validate_session(session_id: Optional[str]) -> Optional[CurrentUser]:
        """
        Validate session and return current user.
        
        Args:
            session_id: Session ID from cookie
            
        Returns:
            CurrentUser if valid, None if invalid/expired
        """
        if not session_id:
            return None
        
        # Retrieve session from secure storage
        session_data = await session_store.get_session(session_id)
        if not session_data:
            return None
        
        # Check if session has expired
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.utcnow() > expires_at:
            # Clean up expired session
            await session_store.delete_session(session_id)
            return None
        
        # Update last accessed time
        session_data["last_accessed"] = datetime.utcnow().isoformat()
        await session_store.update_session(session_id, session_data)
        
        return CurrentUser(
            id=session_data["user_id"],
            email=session_data["email"],
            session_id=session_id
        )
    
    @staticmethod
    async def logout_user(session_id: str) -> bool:
        """
        Logout user and clear session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if successful
        """
        try:
            await session_store.delete_session(session_id)
            return True
        except Exception:
            # Log error but still return True to clear frontend state
            return True
    
    @staticmethod
    async def refresh_session(session_id: str) -> AuthResult:
        """
        Refresh expired access token using stored refresh token.
        
        Args:
            session_id: Current session ID
            
        Returns:
            AuthResult with success/failure info
        """
        try:
            # Get current session data
            session_data = await session_store.get_session(session_id)
            if not session_data:
                return AuthResult(success=False, error_message="Session not found")
            
            # Note: This is simplified - you'd need to store refresh token encrypted
            # and implement proper refresh logic with Cognito
            refresh_token = session_data.get("refresh_token_encrypted")
            if not refresh_token:
                return AuthResult(success=False, error_message="No refresh token")
            
            # Exchange refresh token for new access token
            new_tokens = await AuthService._refresh_cognito_tokens(refresh_token)
            
            # Update session with new access token
            session_data["access_token"] = encrypt_token(new_tokens["access_token"])
            session_data["expires_at"] = (
                datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
            ).isoformat()
            
            # Save updated session
            await session_store.update_session(
                session_id, 
                session_data,
                ttl=new_tokens["expires_in"]
            )
            
            return AuthResult(success=True)
            
        except Exception as e:
            # If refresh fails, session is invalid
            await session_store.delete_session(session_id)
            return AuthResult(success=False, error_message="Token refresh failed")
    
    # Private helper methods
    @staticmethod
    async def _exchange_code_for_tokens(auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh/ID tokens."""
        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.cognito_client_id,
            "client_secret": settings.cognito_client_secret,
            "code": auth_code,
            "redirect_uri": settings.api_callback_url
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{settings.cognito_domain}/oauth2/token",
                data=token_data,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else {}
                raise ValueError(f"Token exchange failed: {error_data.get('error', 'Unknown error')}")
            
            return response.json()
    
    @staticmethod
    async def _decode_and_validate_id_token(id_token: str) -> UserInfo:
        """Decode and validate Cognito ID token."""
        try:
            # Get Cognito public keys for token validation
            jwks = await AuthService._get_cognito_jwks()
            
            # Decode header to get key ID
            header = jwt.get_unverified_header(id_token)
            kid = header.get("kid")
            
            # Find matching public key
            public_key = None
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                raise ValueError("Could not find matching public key")
            
            # Decode and validate token
            payload = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=settings.cognito_client_id,
                issuer=f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"
            )
            
            return UserInfo(
                sub=payload["sub"],
                email=payload["email"],
                given_name=payload.get("given_name", ""),
                family_name=payload.get("family_name", "")
            )
            
        except Exception as e:
            raise ValueError(f"Invalid ID token: {str(e)}")
    
    @staticmethod
    async def _get_cognito_jwks() -> Dict[str, Any]:
        """Get Cognito JSON Web Key Set for token validation."""
        jwks_url = f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}/.well-known/jwks.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    async def _create_user_session(user_info: UserInfo, tokens: Dict[str, Any]) -> str:
        """Create secure user session with encrypted tokens."""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_info.sub,
            "email": user_info.email,
            "given_name": user_info.given_name,
            "family_name": user_info.family_name,
            "access_token": encrypt_token(tokens["access_token"]),
            "refresh_token_hash": hash_token(tokens["refresh_token"]),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=tokens["expires_in"])).isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }
        
        await session_store.create_session(
            session_id=session_id, 
            session_data=session_data, 
            ttl=tokens["expires_in"]
        )
        
        return session_id
    
    @staticmethod
    async def _refresh_cognito_tokens(refresh_token: str) -> Dict[str, Any]:
        """Get new access token using refresh token."""
        token_data = {
            "grant_type": "refresh_token",
            "client_id": settings.cognito_client_id,
            "client_secret": settings.cognito_client_secret,
            "refresh_token": refresh_token
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{settings.cognito_domain}/oauth2/token",
                data=token_data,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise ValueError("Refresh token invalid or expired")
            
            return response.json()
```

### Request/Response Schemas (app/schemas/auth.py)

```python
# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserInfo(BaseModel):
    sub: str
    email: EmailStr
    given_name: Optional[str] = ""
    family_name: Optional[str] = ""

class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int
    token_type: str = "Bearer"

class AuthCheckResponse(BaseModel):
    authenticated: bool
    user: Optional[dict] = None

class AuthCallbackRequest(BaseModel):
    code: str
    state: str

class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
```

### Thin Authentication Router (app/routers/auth.py)

```python
# app/routers/auth.py
"""
Thin authentication router - HTTP wrapper around AuthService.
Contains minimal logic, delegates to service layer.
"""
from fastapi import APIRouter, HTTPException, Response, Request, Depends, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional

from app.services.auth_service import AuthService, CurrentUser
from app.schemas.auth import AuthCheckResponse, AuthResponse
from app.core.config import settings

router = APIRouter(tags=["authentication"])

@router.get("/auth/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate OAuth login flow."""
    cognito_url, _ = await AuthService.initiate_login(request.client.host)
    return RedirectResponse(url=cognito_url, status_code=302)

@router.get("/auth/callback")
async def auth_callback(
    code: str,
    state: str,
    request: Request,
    error: Optional[str] = None,
    error_description: Optional[str] = None
) -> RedirectResponse:
    """Handle OAuth callback."""
    # Handle OAuth errors
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error={error}&description={error_description}"
        )
    
    # Process callback through service
    result = await AuthService.handle_oauth_callback(code, state, request.client.host)
    
    # Create response with redirect
    response = RedirectResponse(url=result.redirect_url, status_code=302)
    
    # Set session cookie if successful
    if result.success and result.session_id:
        response.set_cookie(
            key="session_id",
            value=result.session_id,
            max_age=3600,  # 1 hour
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            domain=settings.cookie_domain,
            path="/"
        )
    
    return response

@router.post("/auth/logout")
async def logout(
    response: Response,
    current_user: CurrentUser = Depends(get_current_user)
) -> AuthResponse:
    """Logout user and clear session."""
    success = await AuthService.logout_user(current_user.session_id)
    
    # Clear HTTPOnly cookie
    response.delete_cookie(
        key="session_id",
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/"
    )
    
    return AuthResponse(success=success, message="Logged out successfully")

@router.get("/auth/check")
async def check_auth(current_user: CurrentUser = Depends(get_current_user)) -> AuthCheckResponse:
    """Check authentication status."""
    return AuthCheckResponse(
        authenticated=True,
        user={"id": current_user.id, "email": current_user.email}
    )

@router.post("/auth/refresh")
async def refresh_session(
    current_user: CurrentUser = Depends(get_current_user)
) -> AuthResponse:
    """Refresh access token."""
    result = await AuthService.refresh_session(current_user.session_id)
    
    if not result.success:
        raise HTTPException(status_code=401, detail=result.error_message)
    
    return AuthResponse(success=True, message="Token refreshed")

# Dependency for authentication
async def get_current_user(
    session_id: Optional[str] = Cookie(None, alias="session_id")
) -> CurrentUser:
    """Get current authenticated user from session."""
    user = await AuthService.validate_session(session_id)
    
    if not user:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"}
        )
    
    return user

# Example of protected endpoint using the dependency
@router.get("/profile")
async def get_user_profile(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Example protected endpoint."""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "session_id": current_user.session_id[:8] + "..."  # Partial for debugging
    }

@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    session_id: str

# ═══════════════════════════════════════════════════════════════
# OAUTH FLOW HANDLERS
# ═══════════════════════════════════════════════════════════════

@router.get("/auth/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate OAuth flow with state for CSRF protection."""
    
    # Generate secure state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state temporarily (5 min expiration)
    await session_store.store_temp_state(
        state=state,
        client_ip=request.client.host,
        expires_in=300  # 5 minutes
    )
    
    # Build Cognito login URL with all required parameters
    cognito_url = (
        f"https://{settings.cognito_domain}/login?"
        f"client_id={settings.cognito_client_id}&"
        f"response_type=code&"
        f"scope=openid+email+profile&"
        f"redirect_uri={settings.api_callback_url}&"
        f"state={state}&"
        f"identity_provider=Google"  # Force Google login
    )
    
    return RedirectResponse(url=cognito_url, status_code=302)

@router.get("/auth/callback")
async def auth_callback(
    code: str,
    state: str,
    request: Request,
    error: Optional[str] = None,
    error_description: Optional[str] = None
) -> RedirectResponse:
    """Handle OAuth callback and create secure session."""
    
    # Handle OAuth errors
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error={error}&description={error_description}"
        )
    
    # Verify state parameter (CSRF protection)
    if not await session_store.verify_temp_state(state, request.client.host):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    try:
        # Exchange authorization code for tokens
        tokens = await exchange_code_for_tokens(code)
        
        # Decode and validate ID token
        user_info = await decode_and_validate_id_token(tokens["id_token"])
        
        # Create secure session
        session_id = await create_user_session(
            user_id=user_info["sub"],
            email=user_info["email"],
            given_name=user_info.get("given_name", ""),
            family_name=user_info.get("family_name", ""),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"]
        )
        
        # Clean up temporary state
        await session_store.delete_temp_state(state)
        
        # Redirect to frontend with secure session cookie
        response = RedirectResponse(
            url=f"{settings.frontend_url}/dashboard",
            status_code=302
        )
        
        # Set HTTPOnly session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=tokens["expires_in"],
            httponly=True,                    # Prevent XSS access
            secure=settings.secure_cookies,   # HTTPS only in production
            samesite="lax",                   # CSRF protection
            domain=settings.cookie_domain,    # Domain scope
            path="/"                          # Available to all paths
        )
        
        return response
        
    except Exception as e:
        # Log error for debugging
        print(f"OAuth callback error: {str(e)}")
        
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?reason=oauth_failed"
        )

@router.post("/auth/logout")
async def logout(
    response: Response,
    current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Logout user and clear session."""
    
    try:
        # Revoke session from storage
        await session_store.delete_session(current_user.session_id)
        
        # Clear HTTPOnly cookie
        response.delete_cookie(
            key="session_id",
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            domain=settings.cookie_domain,
            path="/"
        )
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        # Still clear cookie even if session deletion fails
        response.delete_cookie(
            key="session_id",
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            domain=settings.cookie_domain
        )
        
        return {"success": True, "message": "Logged out"}

@router.get("/auth/check")
async def check_auth(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Check if user is authenticated (for frontend auth state)."""
    return {
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email
        }
    }

# ═══════════════════════════════════════════════════════════════
# TOKEN EXCHANGE AND VALIDATION
# ═══════════════════════════════════════════════════════════════

async def exchange_code_for_tokens(auth_code: str) -> dict:
    """Exchange authorization code for access/refresh/ID tokens."""
    
    # Prepare token exchange request
    token_data = {
        "grant_type": "authorization_code",
        "client_id": settings.cognito_client_id,
        "client_secret": settings.cognito_client_secret,
        "code": auth_code,
        "redirect_uri": settings.api_callback_url
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Make token exchange request to Cognito
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data=token_data,
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.headers.get("content-type") == "application/json" else {}
            raise HTTPException(
                status_code=400, 
                detail=f"Token exchange failed: {error_data.get('error', 'Unknown error')}"
            )
        
        return response.json()

async def decode_and_validate_id_token(id_token: str) -> dict:
    """Decode and validate Cognito ID token."""
    
    try:
        # Get Cognito public keys for token validation
        jwks = await get_cognito_jwks()
        
        # Decode header to get key ID
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        
        # Find matching public key
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
        
        if not public_key:
            raise ValueError("Could not find matching public key")
        
        # Decode and validate token
        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"
        )
        
        return payload
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ID token: {str(e)}")

async def get_cognito_jwks() -> dict:
    """Get Cognito JSON Web Key Set for token validation."""
    
    jwks_url = f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        return response.json()

# ═══════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════

async def create_user_session(
    user_id: str,
    email: str,
    given_name: str,
    family_name: str,
    access_token: str,
    refresh_token: str,
    expires_in: int
) -> str:
    """Create secure user session with encrypted tokens."""
    
    # Generate cryptographically secure session ID
    session_id = secrets.token_urlsafe(32)
    
    # Prepare session data with security measures
    session_data = {
        "user_id": user_id,
        "email": email,
        "given_name": given_name,
        "family_name": family_name,
        # Encrypt sensitive tokens before storage
        "access_token": encrypt_token(access_token),
        "refresh_token_hash": hash_token(refresh_token),  # Hash refresh token
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
        "last_accessed": datetime.utcnow().isoformat()
    }
    
    # Store session with automatic expiration
    await session_store.create_session(
        session_id=session_id, 
        session_data=session_data, 
        ttl=expires_in
    )
    
    return session_id

async def get_current_user(
    session_id: Optional[str] = Cookie(None, alias="session_id")
) -> CurrentUser:
    """Extract authenticated user from secure session cookie."""
    
    if not session_id:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"}
        )
    
    # Retrieve session from secure storage
    session_data = await session_store.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=401, 
            detail="Invalid session"
        )
    
    # Check if session has expired
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    if datetime.utcnow() > expires_at:
        # Clean up expired session
        await session_store.delete_session(session_id)
        raise HTTPException(
            status_code=401, 
            detail="Session expired"
        )
    
    # Update last accessed time
    session_data["last_accessed"] = datetime.utcnow().isoformat()
    await session_store.update_session(session_id, session_data)
    
    return CurrentUser(
        id=session_data["user_id"],
        email=session_data["email"],
        session_id=session_id
    )

# ═══════════════════════════════════════════════════════════════
# TOKEN REFRESH (Background Process)
# ═══════════════════════════════════════════════════════════════

@router.post("/auth/refresh")
async def refresh_session(
    current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Refresh expired access token using stored refresh token."""
    
    try:
        # Get current session data
        session_data = await session_store.get_session(current_user.session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="Session not found")
        
        # Decrypt refresh token for use
        refresh_token_hash = session_data["refresh_token_hash"]
        # Note: You'd need to store the actual refresh token encrypted, not just hashed
        # This is a simplified example - in practice, encrypt rather than hash refresh tokens
        
        # Exchange refresh token for new access token
        new_tokens = await refresh_cognito_tokens(refresh_token_hash)
        
        # Update session with new access token
        session_data["access_token"] = encrypt_token(new_tokens["access_token"])
        session_data["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
        ).isoformat()
        
        # Save updated session
        await session_store.update_session(
            current_user.session_id, 
            session_data,
            ttl=new_tokens["expires_in"]
        )
        
        return {"success": True, "expires_in": new_tokens["expires_in"]}
        
    except Exception as e:
        # If refresh fails, session is invalid
        await session_store.delete_session(current_user.session_id)
        raise HTTPException(status_code=401, detail="Token refresh failed")

async def refresh_cognito_tokens(refresh_token: str) -> dict:
    """Get new access token using refresh token."""
    
    token_data = {
        "grant_type": "refresh_token",
        "client_id": settings.cognito_client_id,
        "client_secret": settings.cognito_client_secret,
        "refresh_token": refresh_token
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data=token_data,
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise ValueError("Refresh token invalid or expired")
        
        return response.json()

# ═══════════════════════════════════════════════════════════════
# PROTECTED ENDPOINT EXAMPLE
# ═══════════════════════════════════════════════════════════════

@router.get("/profile")
async def get_user_profile(
    current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Example protected endpoint - get user profile."""
    
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "profile": {
            "authenticated": True,
            "session_id": current_user.session_id[:8] + "...",  # Partial for debugging
        }
    }
```

## Session Storage Implementation

### Redis Session Store (app/core/session.py)

```python
# app/core/session.py
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.config import settings

class SessionStore:
    """Secure session storage using Redis."""
    
    def __init__(self):
        self.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    async def create_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any], 
        ttl: int
    ) -> None:
        """Create new session with automatic expiration."""
        
        serialized_data = json.dumps(session_data, default=str)
        
        await self.redis.setex(
            f"session:{session_id}",
            ttl,
            serialized_data
        )
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data."""
        
        data = await self.redis.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    
    async def update_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> None:
        """Update existing session data."""
        
        serialized_data = json.dumps(session_data, default=str)
        
        if ttl:
            await self.redis.setex(f"session:{session_id}", ttl, serialized_data)
        else:
            await self.redis.set(f"session:{session_id}", serialized_data)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session (logout)."""
        await self.redis.delete(f"session:{session_id}")
    
    async def store_temp_state(
        self, 
        state: str, 
        client_ip: str, 
        expires_in: int
    ) -> None:
        """Store temporary OAuth state for CSRF protection."""
        
        state_data = {
            "client_ip": client_ip,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.setex(
            f"oauth_state:{state}",
            expires_in,
            json.dumps(state_data)
        )
    
    async def verify_temp_state(self, state: str, client_ip: str) -> bool:
        """Verify OAuth state parameter."""
        
        data = await self.redis.get(f"oauth_state:{state}")
        if not data:
            return False
        
        state_data = json.loads(data)
        
        # Verify IP matches (optional security measure)
        if state_data.get("client_ip") != client_ip:
            return False
        
        return True
    
    async def delete_temp_state(self, state: str) -> None:
        """Clean up temporary state."""
        await self.redis.delete(f"oauth_state:{state}")

# Global session store instance
session_store = SessionStore()
```

## Security Utilities (app/core/crypto.py)

```python
# app/core/crypto.py
import secrets
import hashlib
from cryptography.fernet import Fernet
import base64

from app.core.config import settings

# Initialize encryption with key from settings
fernet = Fernet(settings.session_encryption_key.encode())

def encrypt_token(token: str) -> str:
    """Encrypt sensitive tokens before storage."""
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt tokens for use."""
    return fernet.decrypt(encrypted_token.encode()).decode()

def hash_token(token: str) -> str:
    """Generate salted SHA-256 hash of a token.
    
    Format: salt:hash where both salt and hash are hex-encoded.
    The salt is 32 bytes (64 hex chars) and hash is 32 bytes (64 hex chars).
    """
    salt = secrets.token_bytes(32)
    hash_bytes = hashlib.sha256(salt + token.encode("utf-8")).digest()
    return f"{salt.hex()}:{hash_bytes.hex()}"

def verify_token(token: str, stored_hash: str) -> bool:
    """Verify a token against a stored salted hash."""
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        stored_hash_bytes = bytes.fromhex(hash_hex)
        
        computed_hash = hashlib.sha256(salt + token.encode("utf-8")).digest()
        return secrets.compare_digest(computed_hash, stored_hash_bytes)
    except (ValueError, TypeError):
        return False
```

## Configuration Settings

### Environment Configuration (app/core/config.py)

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # AWS Cognito Configuration
    aws_region: str = "us-east-1"
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_client_secret: str
    cognito_domain: str  # e.g., "play-later-dev.auth.us-east-1.amazoncognito.com"
    
    # OAuth URLs
    api_callback_url: str
    frontend_url: str
    
    # Session Security
    session_encryption_key: str  # Base64 encoded 32-byte key
    cookie_domain: str = "localhost"  # "localhost" for dev, ".yourdomain.com" for prod
    secure_cookies: bool = False  # False for dev (HTTP), True for prod (HTTPS)
    
    # Session Storage
    redis_url: str = "redis://localhost:6379/0"
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Local Development Configuration

### Development Environment Setup

#### .env.development
```bash
# AWS Cognito (from Terraform outputs)
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_AbCdEfGhI
COGNITO_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m
COGNITO_CLIENT_SECRET=your-client-secret-here
COGNITO_DOMAIN=play-later-dev.auth.us-east-1.amazoncognito.com

# OAuth Configuration (localhost)
API_CALLBACK_URL=http://localhost:8000/auth/callback
FRONTEND_URL=http://localhost:3000

# Session Security (relaxed for development)
SESSION_ENCRYPTION_KEY=your-base64-encoded-32-byte-key
COOKIE_DOMAIN=localhost
SECURE_COOKIES=false
REDIS_URL=redis://localhost:6379/1

# Environment
ENVIRONMENT=development
```

#### CORS Configuration for Development
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.auth import router as auth_router

app = FastAPI(title="Play Later API")

# Development CORS
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ],
        allow_credentials=True,  # Essential for HTTPOnly cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add auth router
app.include_router(auth_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Play Later API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## Development Workflow

### 1. Start Services
```bash
# Terminal 1: Start Redis
redis-server --port 6379

# Terminal 2: Start API
cd api/
source .venv/bin/activate
export $(cat .env.development | xargs)
poetry run uvicorn app.main:app --reload --port 8000

# Terminal 3: Check logs
tail -f /var/log/redis/redis-server.log  # or wherever Redis logs
```

### 2. Test OAuth Flow
```bash
# 1. Start login flow
curl -X GET "http://localhost:8000/api/v1/auth/login" -v -L

# 2. Test auth check (after completing OAuth in browser)
curl -X GET "http://localhost:8000/api/v1/auth/check" \
  -H "Cookie: session_id=your-session-id" \
  -v

# 3. Test logout
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Cookie: session_id=your-session-id" \
  -v
```

### 3. Debug Session Storage
```bash
# Connect to Redis and inspect sessions
redis-cli -p 6379 -n 1

# List all sessions
KEYS session:*

# View session data
GET session:your-session-id

# List OAuth states
KEYS oauth_state:*
```

## Testing Strategy

### Unit Tests
```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.session import session_store

client = TestClient(app)

class TestAuthFlow:
    
    def test_login_redirects_to_cognito(self):
        """Test login endpoint redirects to Cognito."""
        response = client.get("/api/v1/auth/login", allow_redirects=False)
        
        assert response.status_code == 302
        assert "cognito" in response.headers["location"]
        assert "client_id" in response.headers["location"]
        assert "state=" in response.headers["location"]
    
    @patch('app.auth.exchange_code_for_tokens')
    @patch('app.auth.decode_and_validate_id_token')
    async def test_callback_success(self, mock_decode, mock_exchange):
        """Test successful OAuth callback."""
        
        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token", 
            "id_token": "id-token",
            "expires_in": 3600
        }
        
        # Mock ID token decode
        mock_decode.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "given_name": "Test",
            "family_name": "User"
        }
        
        # Store temp state
        await session_store.store_temp_state("test-state", "127.0.0.1", 300)
        
        response = client.get(
            "/api/v1/auth/callback?code=test-code&state=test-state",
            allow_redirects=False
        )
        
        assert response.status_code == 302
        assert "session_id" in response.cookies
        assert response.cookies["session_id"]["httponly"] == True
    
    def test_auth_required_returns_401(self):
        """Test endpoints require authentication."""
        response = client.get("/api/v1/auth/check")
        assert response.status_code == 401
    
    async def test_logout_clears_session(self):
        """Test logout clears session and cookie."""
        # Create test session
        session_id = "test-session-id"
        await session_store.create_session(
            session_id,
            {"user_id": "user-123", "email": "test@example.com"},
            3600
        )
        
        response = client.post(
            "/api/v1/auth/logout",
            cookies={"session_id": session_id}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify session deleted
        session_data = await session_store.get_session(session_id)
        assert session_data is None
```

### Integration Tests
```python
# tests/test_integration.py
import pytest
from unittest.mock import patch
import httpx

class TestCognitoIntegration:
    
    @patch('httpx.AsyncClient.post')
    async def test_token_exchange_success(self, mock_post):
        """Test successful token exchange with Cognito."""
        
        # Mock Cognito response
        mock_response = httpx.Response(
            status_code=200,
            json={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        )
        mock_post.return_value = mock_response
        
        from app.auth import exchange_code_for_tokens
        
        result = await exchange_code_for_tokens("test-auth-code")
        
        assert result["access_token"] == "access-token"
        assert result["expires_in"] == 3600
    
    async def test_session_expiration(self):
        """Test session expiration handling."""
        
        # Create expired session
        from datetime import datetime, timedelta
        
        expired_session_data = {
            "user_id": "user-123",
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        
        await session_store.create_session(
            "expired-session",
            expired_session_data,
            1  # Very short TTL
        )
        
        response = client.get(
            "/api/v1/auth/check",
            cookies={"session_id": "expired-session"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
```

## Production Considerations

### Security Headers
```python
# app/middleware/security.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Security headers for production
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY" 
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
```

### Error Handling
```python
# app/middleware/errors.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with security considerations."""
    
    # Don't expose internal errors in production
    if exc.status_code == 500:
        detail = "Internal server error"
    else:
        detail = exc.detail
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": get_error_type(exc.status_code),
            "message": detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

def get_error_type(status_code: int) -> str:
    """Map status codes to error types."""
    error_map = {
        400: "bad_request",
        401: "authentication_required", 
        403: "forbidden",
        404: "not_found",
        500: "internal_error"
    }
    return error_map.get(status_code, "unknown_error")
```

## Next Steps

1. **Implement session storage**: Set up Redis or database for session management
2. **Add security utilities**: Implement token encryption and hashing
3. **Configure environment**: Set up development and production configurations
4. **Add middleware**: Security headers, error handling, request logging
5. **Write tests**: Unit and integration tests for auth flow

See [ui-implementation.md](./ui-implementation.md) for frontend integration.