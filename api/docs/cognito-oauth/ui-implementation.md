# UI Implementation - React Frontend

## Overview

This document covers the React frontend implementation for the Backend Proxy Pattern authentication. The frontend has minimal auth complexity - it simply redirects to backend endpoints and handles HTTPOnly cookies automatically.

## Implementation Architecture

```
React App → Backend Auth Proxy → Session Cookie → Protected Routes
```

**Key Benefits:**
- No token management in frontend JavaScript
- HTTPOnly cookies handled automatically
- Simple redirect-based flow
- Automatic session validation

## Core Components

### 1. Authentication Service
### 2. Authentication Hooks  
### 3. Protected Components
### 4. Route Guards
### 5. API Client Configuration

## Complete Frontend Implementation

### Authentication Service (src/lib/auth.ts)

```typescript
// src/lib/auth.ts
/**
 * Authentication service for Backend Proxy Pattern.
 * Handles auth flow through backend redirects and HTTPOnly cookies.
 */

export class AuthService {
  private static readonly BASE_URL = '/api/v1';
  private static readonly LOGIN_URL = `${AuthService.BASE_URL}/auth/login`;
  private static readonly LOGOUT_URL = `${AuthService.BASE_URL}/auth/logout`;
  private static readonly CHECK_URL = `${AuthService.BASE_URL}/auth/check`;

  /**
   * Initiate login flow.
   * Redirects to backend which handles OAuth complexity.
   */
  static async initiateLogin(): Promise<void> {
    // Store current location for post-login redirect
    const currentPath = window.location.pathname + window.location.search;
    if (currentPath !== '/login') {
      sessionStorage.setItem('redirectAfterLogin', currentPath);
    }
    
    // Redirect to backend login endpoint
    // Backend handles OAuth state, Cognito redirect, etc.
    window.location.href = this.LOGIN_URL;
  }

  /**
   * Logout user and clear session.
   * Calls backend to clear HTTPOnly cookie and session.
   */
  static async logout(): Promise<void> {
    try {
      const response = await fetch(this.LOGOUT_URL, {
        method: 'POST',
        credentials: 'include'  // Include HTTPOnly cookie
      });

      // Handle logout regardless of response status
      // (Cookie might already be expired, etc.)
      
      // Clear any local storage
      sessionStorage.removeItem('redirectAfterLogin');
      localStorage.removeItem('user');  // If you store any user data
      
      // Redirect to home page
      window.location.href = '/';
      
    } catch (error) {
      console.error('Logout request failed:', error);
      // Still redirect to clear local state
      window.location.href = '/';
    }
  }

  /**
   * Check if user is currently authenticated.
   * Uses backend endpoint with HTTPOnly cookie.
   */
  static async checkAuth(): Promise<{
    authenticated: boolean;
    user?: { id: string; email: string };
  }> {
    try {
      const response = await fetch(this.CHECK_URL, {
        method: 'GET',
        credentials: 'include',  // Include HTTPOnly cookie
        cache: 'no-cache'       // Always check fresh status
      });

      if (response.ok) {
        const data = await response.json();
        return {
          authenticated: true,
          user: data.user
        };
      } else {
        return { authenticated: false };
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      return { authenticated: false };
    }
  }

  /**
   * Handle post-login redirect.
   * Called after successful OAuth callback.
   */
  static handleLoginSuccess(): void {
    const redirectPath = sessionStorage.getItem('redirectAfterLogin');
    sessionStorage.removeItem('redirectAfterLogin');
    
    // Redirect to original destination or dashboard
    const targetPath = redirectPath && redirectPath !== '/login' 
      ? redirectPath 
      : '/dashboard';
      
    window.location.href = targetPath;
  }

  /**
   * Handle login error.
   * Called when OAuth flow fails.
   */
  static handleLoginError(error?: string, description?: string): void {
    console.error('Login failed:', { error, description });
    
    // Clear any stored redirect
    sessionStorage.removeItem('redirectAfterLogin');
    
    // Show error to user (you might want to use a toast/notification)
    alert(`Login failed: ${description || error || 'Unknown error'}`);
    
    // Redirect to login page
    window.location.href = '/login';
  }
}
```

### Authentication Hook (src/hooks/useAuth.ts)

```typescript
// src/hooks/useAuth.ts
import { useState, useEffect, useCallback, useContext, createContext, type ReactNode } from 'react';
import { AuthService } from '@/lib/auth';

interface User {
  id: string;
  email: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Auth Provider Component
 * Manages authentication state for the entire app.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [user, setUser] = useState<User | null>(null);

  /**
   * Check authentication status
   */
  const checkAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      const authResult = await AuthService.checkAuth();
      
      setIsAuthenticated(authResult.authenticated);
      setUser(authResult.user || null);
    } catch (error) {
      console.error('Auth check failed:', error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Login function
   */
  const login = useCallback(async () => {
    await AuthService.initiateLogin();
  }, []);

  /**
   * Logout function
   */
  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await AuthService.logout();
      // AuthService.logout() redirects, so this won't execute
      // But kept for completeness
      setIsAuthenticated(false);
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Refresh auth state (for manual refresh)
   */
  const refreshAuth = useCallback(async () => {
    await checkAuth();
  }, [checkAuth]);

  // Check auth on mount and when tab becomes visible
  useEffect(() => {
    checkAuth();

    // Check auth when tab becomes visible (handles logout in other tabs)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        checkAuth();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [checkAuth]);

  const value: AuthState = {
    isAuthenticated,
    isLoading,
    user,
    login,
    logout,
    refreshAuth
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to use auth context
 */
export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

/**
 * Hook for protected components that require authentication
 */
export function useRequireAuth(): AuthState {
  const auth = useAuth();
  
  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      // Store current location for redirect after login
      const currentPath = window.location.pathname + window.location.search;
      sessionStorage.setItem('redirectAfterLogin', currentPath);
      
      // Redirect to login
      window.location.href = '/login';
    }
  }, [auth.isAuthenticated, auth.isLoading]);

  return auth;
}
```

### Authentication Components

#### Login Button (src/components/auth/LoginButton.tsx)
```typescript
// src/components/auth/LoginButton.tsx
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';

export function LoginButton() {
  const { login, isLoading } = useAuth();

  return (
    <Button 
      onClick={login}
      disabled={isLoading}
      className="min-w-[200px]"
    >
      {isLoading ? (
        <>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
          Signing in...
        </>
      ) : (
        <>
          <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
            {/* Google icon SVG */}
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Sign in with Google
        </>
      )}
    </Button>
  );
}
```

#### User Menu (src/components/auth/UserMenu.tsx)
```typescript
// src/components/auth/UserMenu.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/hooks/useAuth';

export function UserMenu() {
  const { user, logout, isLoading } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  if (!user) {
    return <LoginButton />;
  }

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      // logout() redirects, so this won't execute
    } catch (error) {
      console.error('Logout failed:', error);
      setIsLoggingOut(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm">
            {user.email.charAt(0).toUpperCase()}
          </div>
          <span className="hidden md:block">{user.email}</span>
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem disabled>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">{user.email}</p>
            <p className="text-xs text-gray-500">ID: {user.id}</p>
          </div>
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem asChild>
          <a href="/profile">Profile Settings</a>
        </DropdownMenuItem>
        
        <DropdownMenuItem asChild>
          <a href="/games">My Games</a>
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem 
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="text-red-600 focus:text-red-600"
        >
          {isLoggingOut ? (
            <>
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-red-600 mr-2" />
              Signing out...
            </>
          ) : (
            'Sign out'
          )}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Re-export LoginButton for convenience
export { LoginButton } from './LoginButton';
```

### Route Protection

#### Protected Route Component (src/components/auth/ProtectedRoute.tsx)
```typescript
// src/components/auth/ProtectedRoute.tsx
import { type ReactNode } from 'react';
import { useRequireAuth } from '@/hooks/useAuth';

interface ProtectedRouteProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useRequireAuth();

  if (isLoading) {
    return (
      fallback || (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <span className="ml-2">Loading...</span>
        </div>
      )
    );
  }

  if (!isAuthenticated) {
    // useRequireAuth handles redirect, but we render fallback just in case
    return (
      fallback || (
        <div className="flex items-center justify-center min-h-screen">
          <p>Redirecting to login...</p>
        </div>
      )
    );
  }

  return <>{children}</>;
}
```

#### Login Guard (src/components/auth/LoginGuard.tsx)
```typescript
// src/components/auth/LoginGuard.tsx
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';

interface LoginGuardProps {
  children: ReactNode;
  redirectTo?: string;
}

/**
 * Redirects authenticated users away from login/public pages
 */
export function LoginGuard({ children, redirectTo = '/dashboard' }: LoginGuardProps) {
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      window.location.href = redirectTo;
    }
  }, [isAuthenticated, isLoading, redirectTo]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p>Redirecting to dashboard...</p>
      </div>
    );
  }

  return <>{children}</>;
}
```

### Page Components

#### Login Page (src/routes/login.tsx)
```typescript
// src/routes/login.tsx
import { LoginGuard } from '@/components/auth/LoginGuard';
import { LoginButton } from '@/components/auth/LoginButton';

export default function LoginPage() {
  return (
    <LoginGuard>
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Sign in to Play Later
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Track and organize your gaming backlog
            </p>
          </div>
          
          <div className="mt-8 space-y-6">
            <div className="flex justify-center">
              <LoginButton />
            </div>
            
            <div className="text-xs text-gray-500 text-center">
              By signing in, you agree to our Terms of Service and Privacy Policy.
            </div>
          </div>
        </div>
      </div>
    </LoginGuard>
  );
}
```

#### Auth Error Page (src/routes/auth/error.tsx)
```typescript
// src/routes/auth/error.tsx  
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { AuthService } from '@/lib/auth';

export default function AuthErrorPage() {
  const [error, setError] = useState<string>('');
  const [description, setDescription] = useState<string>('');

  useEffect(() => {
    // Parse error from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const errorParam = urlParams.get('error') || urlParams.get('reason') || 'unknown_error';
    const descriptionParam = urlParams.get('description') || urlParams.get('error_description') || '';
    
    setError(errorParam);
    setDescription(descriptionParam);

    // Call error handler
    AuthService.handleLoginError(errorParam, descriptionParam);
  }, []);

  const handleRetry = () => {
    AuthService.initiateLogin();
  };

  const getErrorMessage = (error: string): string => {
    switch (error) {
      case 'access_denied':
        return 'Access was denied. You may have cancelled the login process.';
      case 'oauth_failed':
        return 'Authentication failed. Please try again.';
      case 'invalid_request':
        return 'Invalid authentication request.';
      case 'server_error':
        return 'Server error occurred during authentication.';
      default:
        return 'An unexpected error occurred during login.';
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 text-red-600">
            {/* Error icon */}
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.502 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Login Failed
          </h2>
          
          <p className="mt-2 text-sm text-gray-600">
            {getErrorMessage(error)}
          </p>
          
          {description && (
            <p className="mt-1 text-xs text-gray-500">
              Details: {description}
            </p>
          )}
        </div>
        
        <div className="mt-8 space-y-4">
          <Button onClick={handleRetry} className="w-full">
            Try Again
          </Button>
          
          <Button variant="outline" onClick={() => window.location.href = '/'} className="w-full">
            Go Home
          </Button>
        </div>
      </div>
    </div>
  );
}
```

#### Dashboard Page (src/routes/dashboard.tsx)
```typescript
// src/routes/dashboard.tsx
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { UserMenu } from '@/components/auth/UserMenu';
import { useAuth } from '@/hooks/useAuth';

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <h1 className="text-3xl font-bold text-gray-900">
                Dashboard
              </h1>
              <UserMenu />
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Welcome back, {user?.email}!
                </h2>
                
                <div className="mt-4">
                  <p className="text-sm text-gray-600">
                    Your gaming backlog and progress will be displayed here.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
```

## API Client Configuration

### HTTP Client Setup (src/lib/api.ts)

```typescript
// src/lib/api.ts
/**
 * API client configured for HTTPOnly cookie authentication
 */

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1') {
    this.baseUrl = baseUrl;
  }

  /**
   * Make authenticated request with HTTPOnly cookies
   */
  async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      credentials: 'include', // Always include HTTPOnly cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    const requestOptions = { ...defaultOptions, ...options };

    try {
      const response = await fetch(url, requestOptions);

      // Handle authentication errors
      if (response.status === 401) {
        // Session expired or invalid
        this.handleAuthError();
        throw new Error('Authentication required');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return { data };

    } catch (error) {
      console.error('API request failed:', error);
      return { 
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Handle authentication errors
   */
  private handleAuthError() {
    // Clear any local auth state
    sessionStorage.removeItem('redirectAfterLogin');
    
    // Redirect to login if not already there
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  // Convenience methods
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types for use in components
export type { ApiResponse };
```

### Generated API Client Integration

```typescript
// src/lib/generated-api.ts
/**
 * Integration with generated API client from OpenAPI schema
 */
import { createClient } from '@/shared/api/generated';

// Create client with HTTPOnly cookie support
export const generatedApiClient = createClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  credentials: 'include', // Include HTTPOnly cookies
});

// Add response interceptor for auth errors
generatedApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Session expired - redirect to login
      if (window.location.pathname !== '/login') {
        sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

## App Integration

### Main App Setup (src/App.tsx)

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/hooks/useAuth';

// Pages
import HomePage from '@/routes/home';
import LoginPage from '@/routes/login';
import DashboardPage from '@/routes/dashboard';
import AuthErrorPage from '@/routes/auth/error';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/auth/error" element={<AuthErrorPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
```

### Environment Configuration

#### Development (.env.development)
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=Play Later
VITE_ENVIRONMENT=development
```

#### Production (.env.production)
```bash
VITE_API_BASE_URL=https://api.play-later.com/api/v1
VITE_APP_NAME=Play Later
VITE_ENVIRONMENT=production
```

## Development Workflow

### 1. Start Development Server
```bash
# Terminal 1: Start API (see api-implementation.md)
cd api/
source .venv/bin/activate
poetry run uvicorn app.main:app --reload --port 8000

# Terminal 2: Start Frontend
cd web/
pnpm dev --port 3000
```

### 2. Test Authentication Flow
1. Visit `http://localhost:3000`
2. Click "Sign in with Google"
3. Complete OAuth flow in browser
4. Should redirect back to dashboard with session

### 3. Debug Issues
```bash
# Check browser network tab for API calls
# Look for:
# - 401 responses (session issues)
# - CORS errors (middleware config)
# - Cookie not being sent (credentials: 'include')

# Check browser application tab
# - Cookies section should show session_id cookie
# - HTTPOnly flag should be true
# - Secure flag based on environment

# Check console for errors
# - Authentication state updates
# - Redirect loops
# - Network failures
```

## Testing Strategy

### Component Tests
```typescript
// src/components/auth/__tests__/LoginButton.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { LoginButton } from '../LoginButton';
import { useAuth } from '@/hooks/useAuth';

// Mock useAuth hook
vi.mock('@/hooks/useAuth');

describe('LoginButton', () => {
  it('renders login button when not loading', () => {
    vi.mocked(useAuth).mockReturnValue({
      login: vi.fn(),
      isLoading: false,
      isAuthenticated: false,
      user: null,
      logout: vi.fn(),
      refreshAuth: vi.fn()
    });

    render(<LoginButton />);
    
    expect(screen.getByText('Sign in with Google')).toBeInTheDocument();
  });

  it('shows loading state when loading', () => {
    vi.mocked(useAuth).mockReturnValue({
      login: vi.fn(),
      isLoading: true,
      isAuthenticated: false,
      user: null,
      logout: vi.fn(),
      refreshAuth: vi.fn()
    });

    render(<LoginButton />);
    
    expect(screen.getByText('Signing in...')).toBeInTheDocument();
  });

  it('calls login when clicked', () => {
    const mockLogin = vi.fn();
    vi.mocked(useAuth).mockReturnValue({
      login: mockLogin,
      isLoading: false,
      isAuthenticated: false,
      user: null,
      logout: vi.fn(),
      refreshAuth: vi.fn()
    });

    render(<LoginButton />);
    
    fireEvent.click(screen.getByText('Sign in with Google'));
    expect(mockLogin).toHaveBeenCalledOnce();
  });
});
```

### Integration Tests
```typescript
// src/lib/__tests__/auth.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthService } from '../auth';

// Mock global fetch
global.fetch = vi.fn();

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear sessionStorage
    sessionStorage.clear();
  });

  describe('checkAuth', () => {
    it('returns authenticated user when session is valid', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          authenticated: true,
          user: { id: 'user-123', email: 'test@example.com' }
        })
      };
      
      vi.mocked(fetch).mockResolvedValueOnce(mockResponse as any);

      const result = await AuthService.checkAuth();

      expect(result.authenticated).toBe(true);
      expect(result.user).toEqual({ id: 'user-123', email: 'test@example.com' });
      expect(fetch).toHaveBeenCalledWith('/api/v1/auth/check', {
        method: 'GET',
        credentials: 'include',
        cache: 'no-cache'
      });
    });

    it('returns unauthenticated when session is invalid', async () => {
      const mockResponse = {
        ok: false,
        status: 401
      };
      
      vi.mocked(fetch).mockResolvedValueOnce(mockResponse as any);

      const result = await AuthService.checkAuth();

      expect(result.authenticated).toBe(false);
      expect(result.user).toBeUndefined();
    });
  });

  describe('initiateLogin', () => {
    it('stores current path and redirects to login endpoint', async () => {
      // Mock window.location
      delete (window as any).location;
      window.location = { href: '', pathname: '/games', search: '?filter=action' } as any;

      await AuthService.initiateLogin();

      expect(sessionStorage.getItem('redirectAfterLogin')).toBe('/games?filter=action');
      expect(window.location.href).toBe('/api/v1/auth/login');
    });

    it('does not store login path as redirect', async () => {
      delete (window as any).location;
      window.location = { href: '', pathname: '/login', search: '' } as any;

      await AuthService.initiateLogin();

      expect(sessionStorage.getItem('redirectAfterLogin')).toBeNull();
      expect(window.location.href).toBe('/api/v1/auth/login');
    });
  });
});
```

### E2E Tests with Playwright
```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('complete OAuth login flow', async ({ page }) => {
    // Start at home page
    await page.goto('/');
    
    // Click login button
    await page.click('text=Sign in with Google');
    
    // Should redirect to backend auth endpoint
    // (In real test, you'd need to mock OAuth or use test credentials)
    
    // After OAuth completion, should be at dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Should see user info
    await expect(page.locator('text=Welcome back')).toBeVisible();
  });

  test('protected route redirects to login', async ({ page }) => {
    // Try to access protected route without auth
    await page.goto('/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL('/login');
    
    // Should see login form
    await expect(page.locator('text=Sign in with Google')).toBeVisible();
  });

  test('logout clears session', async ({ page, context }) => {
    // Mock authenticated session
    await context.addCookies([{
      name: 'session_id',
      value: 'mock-session-id',
      domain: 'localhost',
      path: '/'
    }]);
    
    // Visit dashboard
    await page.goto('/dashboard');
    
    // Click logout
    await page.click('text=Sign out');
    
    // Should redirect to home
    await expect(page).toHaveURL('/');
    
    // Session cookie should be cleared
    const cookies = await context.cookies();
    const sessionCookie = cookies.find(c => c.name === 'session_id');
    expect(sessionCookie).toBeUndefined();
  });
});
```

## Production Considerations

### Performance Optimization
```typescript
// src/hooks/useAuth.ts - Add debouncing for auth checks
import { debounce } from 'lodash-es';

const debouncedCheckAuth = debounce(checkAuth, 1000);

// Use in visibility change handler to avoid excessive API calls
const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    debouncedCheckAuth();
  }
};
```

### Error Boundary
```typescript
// src/components/ErrorBoundary.tsx
import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Auth Error Boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-xl font-semibold text-red-600">
              Authentication Error
            </h1>
            <p className="mt-2 text-gray-600">
              Something went wrong with authentication. Please refresh the page.
            </p>
            <button 
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### Security Headers
```typescript
// src/lib/security.ts - Client-side security measures
export const SecurityHeaders = {
  /**
   * Prevent clickjacking
   */
  preventFraming() {
    if (window.self !== window.top) {
      window.top!.location = window.self.location;
    }
  },

  /**
   * Clear sensitive data on page unload
   */
  setupPageUnloadCleanup() {
    window.addEventListener('beforeunload', () => {
      // Clear any sensitive data from memory
      // (Session data is in HTTPOnly cookies, so already secure)
    });
  }
};

// Initialize in main App component
SecurityHeaders.preventFraming();
SecurityHeaders.setupPageUnloadCleanup();
```

## Next Steps

1. **Implement components**: Add authentication components to your React app
2. **Configure routing**: Set up protected and public routes
3. **Test integration**: Verify OAuth flow works end-to-end
4. **Add error handling**: Implement proper error boundaries and fallbacks
5. **Performance testing**: Test with slow networks and edge cases

The frontend implementation is now complete and ready for integration with the backend API!