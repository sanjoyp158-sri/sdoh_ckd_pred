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
        // API call would go here
        // For now, mock authentication
        const mockUser: User = {
          id: '1',
          username,
          role: 'provider',
        };
        const mockToken = 'mock-jwt-token';
        set({ user: mockUser, token: mockToken, isAuthenticated: true });
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
