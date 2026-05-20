import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import api from '../services/api';

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  setIsAuthenticated: (v: boolean) => void;
}

const AuthContext = createContext<AuthContextValue>({
  isAuthenticated: false,
  isLoading: true,
  setIsAuthenticated: () => {},
});

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get('/api/telegram/auth/status')
      .then(res => setIsAuthenticated(!!res.data.authorized))
      .catch(() => setIsAuthenticated(false))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, setIsAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
