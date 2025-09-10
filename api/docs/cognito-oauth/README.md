# AWS Cognito OAuth Authentication Documentation

## Overview

This directory contains documentation for implementing AWS Cognito with Google OAuth using HTTPOnly cookies for secure authentication in the Play Later application.

## Architecture Approach

We recommend **Approach B: Backend Proxy Pattern** for maximum security:

```
Frontend → Backend Auth Proxy → Cognito Hosted UI → Backend Callback → Session Management
```

**Key Benefits:**
- Maximum security - tokens never touch frontend
- HTTPOnly cookies prevent XSS token theft
- Centralized session management
- CSRF protection through OAuth state parameter
- Clean separation of concerns

## Document Structure

### 📚 [Architecture Overview](./architecture-overview.md)
- Three implementation approaches comparison
- Security analysis and recommendations
- High-level flow diagrams

### 🏗️ [Infrastructure Setup](./infrastructure-setup.md) 
- Complete Terraform configuration with detailed explanations
- AWS Cognito resource setup
- Terraform workflow and validation guide
- Common pitfalls and troubleshooting

### 🔧 [API Implementation](./api-implementation.md)
- FastAPI backend code with session management
- OAuth flow handlers and security
- Local development configuration
- Testing strategies

### 🎨 [UI Implementation](./ui-implementation.md)
- React frontend integration
- Authentication hooks and components
- API client configuration
- Route protection

## Quick Start

1. **Setup Infrastructure**: Follow [infrastructure-setup.md](./infrastructure-setup.md) to deploy AWS Cognito
2. **Backend Integration**: Implement API endpoints from [api-implementation.md](./api-implementation.md)  
3. **Frontend Integration**: Add auth components from [ui-implementation.md](./ui-implementation.md)
4. **Local Development**: Configure localhost OAuth flows

## Security Features

- ✅ HTTPOnly cookies (XSS protection)
- ✅ SameSite cookies (CSRF protection) 
- ✅ Secure session management
- ✅ Token encryption/hashing
- ✅ State parameter validation
- ✅ Session expiration handling

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| URLs | `http://localhost:*` | `https://domain.com` |
| Certificates | Not required | Required (HTTPS) |
| Cookie Security | `secure=false` | `secure=true` |
| CORS | Permissive | Restrictive |

## Migration Path

1. **Phase 1**: Infrastructure deployment
2. **Phase 2**: Backend implementation  
3. **Phase 3**: Frontend integration
4. **Phase 4**: Testing and deployment

For detailed implementation steps, see the specific documentation files linked above.