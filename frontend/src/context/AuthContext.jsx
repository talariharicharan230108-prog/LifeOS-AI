import React, { createContext, useContext, useState, useEffect } from 'react';
import * as api from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const token = api.getAuthToken();
    if (!token) return null;
    return api.getSavedUser();
  });
  const [authLoading, setAuthLoading] = useState(() => {
    // If a persistent token exists, start in authLoading state to validate with backend
    return !!api.getAuthToken();
  });

  // Check current session on mount
  useEffect(() => {
    let isMounted = true;
    const initAuth = async () => {
      console.log('[AUTH] AUTH INITIALIZATION');
      const token = api.getAuthToken();
      if (!token) {
        if (isMounted) {
          setUser(null);
          setAuthLoading(false);
        }
        return;
      }
      try {
        const currentUser = await api.fetchCurrentUser();
        if (isMounted) {
          if (currentUser) {
            setUser(currentUser);
            api.setSavedUser(currentUser);
            console.log('[AUTH] AUTH RESTORED');
          } else {
            // Token is invalid/expired
            api.clearAuthToken();
            setUser(null);
          }
        }
      } catch (err) {
        if (err?.status === 401 || err?.status === 403) {
          console.warn('[AUTH] Session expired or invalid:', err);
          api.clearAuthToken();
          if (isMounted) setUser(null);
        } else {
          console.warn('[AUTH] Non-auth error during session validation, preserving session:', err);
          // Preserve saved user session in case backend is restarting or offline
          const saved = api.getSavedUser();
          if (isMounted && saved) {
            setUser(saved);
            console.log('[AUTH] AUTH RESTORED (cached)');
          }
        }
      } finally {
        if (isMounted) {
          setAuthLoading(false);
        }
      }
    };
    initAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email, password) => {
    // Note: Do NOT set authLoading to true here; authLoading is exclusively for startup session checking.
    // AuthPage has its own submitting spinner.
    const res = await api.loginUser({ email, password });
    setUser(res.user);
    return res;
  };

  const register = async ({ name, email, password, confirmPassword }) => {
    const res = await api.registerUser({ name, email, password, confirmPassword });
    setUser(res.user);
    return res;
  };

  const logout = async () => {
    try {
      await api.logoutUser();
    } finally {
      if (user?.id) {
        localStorage.removeItem(`lifeos_local_backup_${user.id}`);
      }
      api.clearAuthToken();
      setUser(null);
    }
  };

  const changePassword = async ({ currentPassword, newPassword, confirmNewPassword }) => {
    return await api.changeUserPassword({ currentPassword, newPassword, confirmNewPassword });
  };

  const updateProfile = async ({ name }) => {
    const res = await api.updateUserProfile({ name });
    if (res?.user) {
      setUser(res.user);
      api.setSavedUser(res.user);
    }
    return res;
  };

  const value = {
    user,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    changePassword,
    updateProfile,
    authLoading,
    loading: authLoading, // backward compatibility
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
