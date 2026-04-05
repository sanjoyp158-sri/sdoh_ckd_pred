import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  username: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string, user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: async (username: string, password: string) => {
        try {
          // Call backend login API
          const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
          });

          if (!response.ok) {
            throw new Error('Login failed');
          }

          const data = await response.json();
          
          // Decode token to get user info (simple base64 decode of JWT payload)
          const tokenParts = data.access_token.split('.');
          const payload = JSON.parse(atob(tokenParts[1]));
          
          const user: User = {
            id: payload.user_id || '1',
            username: payload.sub || username,
            role: payload.role || 'provider',
          };

          set({ user, token: data.access_token, isAuthenticated: true });
        } catch (error) {
          console.error('Login error:', error);
          throw error;
        }
      },
      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },
      setToken: (token: string, user: User) => {
        set({ token, user, isAuthenticated: true });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
