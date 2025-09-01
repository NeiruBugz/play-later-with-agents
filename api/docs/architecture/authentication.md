# Authentication Architecture

## Overview

The Play Later API uses AWS Cognito with **Authorization Code Flow** for secure authentication. The frontend redirects to Cognito Hosted UI, receives an authorization code, sends it to our API, which exchanges it for tokens with Cognito and establishes a secure session.

## Authentication Flow

### 1. Frontend Login Redirect
```javascript
// Frontend redirects user to Cognito Hosted UI
const cognitoLoginUrl = `https://play-later.auth.us-east-1.amazoncognito.com/login?` +
  `client_id=${COGNITO_CLIENT_ID}&` +
  `response_type=code&` +
  `scope=openid+email+profile&` +
  `redirect_uri=${FRONTEND_CALLBACK_URL}`;

window.location.href = cognitoLoginUrl;
```

### 2. Cognito Callback with Authorization Code  
```javascript
// User completes OAuth (Google, etc.) and gets redirected back
// URL: https://play-later.com/auth/callback?code=AUTH_CODE_HERE

const urlParams = new URLSearchParams(window.location.search);
const authCode = urlParams.get('code');

if (authCode) {
  // Send code to our API for token exchange
  const response = await fetch('/api/v1/auth/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: authCode }),
    credentials: 'include' // Important: include cookies
  });
  
  if (response.ok) {
    // Session established via secure cookie
    window.location.href = '/dashboard';
  }
}
```

### 3. Backend Token Exchange & Session Creation
```python
from fastapi import APIRouter, HTTPException, Response, Request
import httpx
import secrets
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/auth/callback")
async def cognito_callback(
    request: AuthCallbackRequest, 
    response: Response
) -> AuthCallbackResponse:
    """Exchange authorization code for tokens and create session."""
    
    # Exchange code for tokens with Cognito
    token_data = await exchange_code_for_tokens(request.code)
    
    # Create secure session
    session_id = secrets.token_urlsafe(32)
    user_id = token_data["id_token_claims"]["sub"]
    
    # Store session in database with hashed tokens
    await store_session(
        session_id=session_id,
        user_id=user_id,
        access_token=token_data["access_token"],  # Consider hashing this too
        refresh_token=token_data["refresh_token"],  # Stored as salted SHA-256 hash
        expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
    )
    
    # Set secure HTTP-only cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=token_data["expires_in"],
        httponly=True,  # Prevents XSS access
        secure=True,    # HTTPS only
        samesite="lax"  # CSRF protection
    )
    
    return AuthCallbackResponse(success=True)

async def exchange_code_for_tokens(auth_code: str) -> dict:
    """Exchange authorization code for access/refresh tokens."""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://play-later.auth.{settings.aws_region}.amazoncognito.com/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.cognito_client_id,
                "client_secret": settings.cognito_client_secret,
                "code": auth_code,
                "redirect_uri": settings.frontend_callback_url
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")
            
        token_data = response.json()
        
        # Decode ID token to get user info
        id_token_claims = decode_cognito_token(token_data["id_token"])
        token_data["id_token_claims"] = id_token_claims
        
        return token_data
```

### 4. Session Storage & Management
```python
from datetime import datetime
from typing import Optional
import redis

class SessionStore:
    """Secure session storage with Redis."""
    
    def __init__(self):
        self.redis = redis.Redis.from_url(settings.redis_url)
    
    async def store_session(
        self,
        session_id: str,
        user_id: str, 
        access_token: str,
        refresh_token: str,
        expires_at: datetime
    ):
        """Store session data with hashed refresh token."""
        session_data = {
            "user_id": user_id,
            "access_token": access_token,  # TODO: Consider hashing
            "refresh_token_hash": hash_token(refresh_token),  # Salted SHA-256 hash
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store with expiration
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        await self.redis.setex(
            f"session:{session_id}",
            ttl,
            json.dumps(session_data)
        )
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data."""
        data = await self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    async def delete_session(self, session_id: str):
        """Delete session (logout)."""
        await self.redis.delete(f"session:{session_id}")

session_store = SessionStore()
```

## API Endpoint Protection

### Session-Based Authentication Middleware
```python
from fastapi import Cookie, HTTPException, Depends
from typing import Optional

class UserContext:
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id

async def get_current_user(
    session_id: Optional[str] = Cookie(None)
) -> UserContext:
    """Extract user from session cookie."""
    
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Retrieve session from storage
    session_data = await session_store.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check if session expired
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    if datetime.utcnow() > expires_at:
        await session_store.delete_session(session_id)
        raise HTTPException(status_code=401, detail="Session expired")
    
    return UserContext(
        user_id=session_data["user_id"],
        session_id=session_id
    )

# Usage in protected endpoints
@router.get("/collection")
async def get_user_collection(
    user: UserContext = Depends(get_current_user)
) -> List[UserGameCollectionResponse]:
    """Get user's game collection."""
    
    collection = await db.query(UserGameCollection).filter(
        UserGameCollection.user_id == user.user_id
    ).all()
    
    return collection
```

### Token Refresh Mechanism
```python
@router.post("/auth/refresh")
async def refresh_session(
    user: UserContext = Depends(get_current_user)
) -> RefreshResponse:
    """Refresh expired access token using refresh token."""
    
    session_data = await session_store.get_session(user.session_id)
    
    # Verify refresh token hash and get plaintext token
    if not verify_refresh_token(user.session_id, provided_refresh_token):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Use refresh token to get new access token
    new_tokens = await refresh_cognito_token(provided_refresh_token)
    
    # Update session with new tokens (refresh token hash remains same)
    await session_store.update_session_tokens(
        session_id=user.session_id,
        access_token=new_tokens["access_token"],
        expires_at=datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
    )
    
    return RefreshResponse(success=True)

async def refresh_cognito_token(refresh_token: str) -> dict:
    """Get new access token using refresh token."""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://play-later.auth.{settings.aws_region}.amazoncognito.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.cognito_client_id,
                "client_secret": settings.cognito_client_secret,
                "refresh_token": refresh_token
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        return response.json()
```

## Logout Flow
```python
@router.post("/auth/logout")
async def logout(
    response: Response,
    user: UserContext = Depends(get_current_user)
):
    """Logout user and clear session."""
    
    # Delete session from storage
    await session_store.delete_session(user.session_id)
    
    # Clear cookie
    response.delete_cookie(
        key="session_id",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return LogoutResponse(success=True)
```

## Frontend API Client
```javascript
class ApiClient {
  // No need to manage tokens - cookies handled automatically
  
  async request(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Always include cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (response.status === 401) {
      // Session expired - redirect to login
      this.handleAuthError();
      return;
    }
    
    return response.json();
  }
  
  async handleAuthError() {
    // Try to refresh first
    const refreshResponse = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include'
    });
    
    if (!refreshResponse.ok) {
      // Refresh failed - redirect to login
      window.location.href = '/login';
    }
  }
}

// Usage - no token management needed
const api = new ApiClient();
const collection = await api.request('/api/v1/collection');
```

## Security Benefits

### Compared to Client-Side JWT:
1. **Tokens never exposed to JavaScript** - Stored securely on server
2. **HTTP-only cookies prevent XSS** - No token theft via malicious scripts
3. **Automatic token refresh** - No expired token handling on frontend
4. **Secure token storage** - Redis/database instead of localStorage
5. **Session invalidation** - Can instantly revoke access

### CSRF Protection:
- `SameSite=Lax` cookie prevents cross-site requests
- Additional CSRF tokens for state-changing operations if needed

## Environment Configuration
```bash
# AWS Cognito
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_AbCdEfGhI
COGNITO_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m
COGNITO_CLIENT_SECRET=secret_key_here
FRONTEND_CALLBACK_URL=https://play-later.com/auth/callback

# Session Storage
REDIS_URL=redis://localhost:6379/0

# Security
COOKIE_DOMAIN=play-later.com
SECURE_COOKIES=true
```

## Database Schema for Sessions (Alternative to Redis)
```sql
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(256),  -- Salted SHA-256 hash (salt:hash format)
    active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
```

### Security Features

#### Refresh Token Hashing
Refresh tokens are stored as salted SHA-256 hashes for security:

```python
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

**Security Benefits:**
- **No plaintext tokens in database** - Even with DB access, tokens can't be read
- **Unique salt per token** - Prevents rainbow table attacks  
- **Constant-time comparison** - Prevents timing attacks
- **Cryptographically secure** - SHA-256 with 32-byte random salt

This approach provides maximum security while maintaining a smooth user experience with automatic session management.