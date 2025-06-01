
// Authentication utilities using HTTP-only cookies
// No localStorage usage for sensitive data

const AuthUtils = {
    // Login function that handles cookie-based authentication
    login: async function(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf_token
                },
                credentials: 'include', // Include cookies
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Token is automatically stored in HTTP-only cookie
                // No need to manually store in localStorage
                return { success: true, user: data.user };
            } else {
                return { success: false, error: data.error || 'Login failed' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: 'Network error during login' };
        }
    },

    // Logout function that clears the HTTP-only cookie
    logout: async function() {
        try {
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf_token
                },
                credentials: 'include'
            });

            const data = await response.json();
            
            if (response.ok) {
                // Cookie is automatically cleared on server side
                // Redirect to login page or home
                window.location.href = '/login';
                return { success: true };
            } else {
                return { success: false, error: data.error || 'Logout failed' };
            }
        } catch (error) {
            console.error('Logout error:', error);
            return { success: false, error: 'Network error during logout' };
        }
    },

    // Check authentication status using HTTP-only cookie
    checkAuth: async function() {
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                return { authenticated: true, user: data.user };
            } else {
                return { authenticated: false };
            }
        } catch (error) {
            console.error('Auth check error:', error);
            return { authenticated: false };
        }
    },

    // Refresh token using HTTP-only cookie
    refreshToken: async function() {
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf_token
                },
                credentials: 'include'
            });

            if (response.ok) {
                // New token is automatically set in HTTP-only cookie
                return { success: true };
            } else {
                return { success: false };
            }
        } catch (error) {
            console.error('Token refresh error:', error);
            return { success: false };
        }
    },

    // Make authenticated API requests
    apiRequest: async function(url, options = {}) {
        const defaultOptions = {
            credentials: 'include', // Always include cookies
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        // Add CSRF token for state-changing requests
        if (options.method && !['GET', 'HEAD', 'OPTIONS'].includes(options.method.toUpperCase())) {
            defaultOptions.headers['X-CSRFToken'] = csrf_token;
        }

        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            // If unauthorized, try to refresh token once
            if (response.status === 401) {
                const refreshResult = await this.refreshToken();
                if (refreshResult.success) {
                    // Retry the original request
                    return await fetch(url, finalOptions);
                } else {
                    // Refresh failed, redirect to login
                    window.location.href = '/login';
                    return response;
                }
            }
            
            return response;
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    }
};

// Auto-refresh token periodically (every 23 hours)
setInterval(async function() {
    const authStatus = await AuthUtils.checkAuth();
    if (authStatus.authenticated) {
        await AuthUtils.refreshToken();
    }
}, 23 * 60 * 60 * 1000); // 23 hours

// Make AuthUtils globally available
window.AuthUtils = AuthUtils;
