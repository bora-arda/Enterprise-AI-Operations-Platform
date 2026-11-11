import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { ApiError, getMe, login as apiLogin, type ApiUser } from '../api/client';
import { AUTH_TOKEN_KEY, CHAT_SESSION_KEY, SESSION_STORAGE_KEY } from '../config';
import type { SessionUser } from '../types';
import { initialsFromName } from '../utils/format';

interface AuthContextValue {
  session: SessionUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string, remember: boolean) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const ROLE_LABELS: Record<string, string> = {
  specialist: 'Specialist',
  manager: 'Manager',
  finance: 'Finance',
  director: 'Director',
  admin: 'Administrator',
};

function toSessionUser(user: ApiUser): SessionUser {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    role: ROLE_LABELS[user.role] ?? user.role,
    initials: initialsFromName(user.name) || user.email.slice(0, 2).toUpperCase(),
  };
}

function readStoredAuth(): { session: SessionUser | null; token: string | null } {
  const stores = [window.localStorage, window.sessionStorage];

  for (const store of stores) {
    try {
      const token = store.getItem(AUTH_TOKEN_KEY);
      const raw = store.getItem(SESSION_STORAGE_KEY);
      if (!token || !raw) continue;
      const parsed = JSON.parse(raw) as Partial<SessionUser>;
      if (
        typeof parsed.id === 'string' &&
        typeof parsed.name === 'string' &&
        typeof parsed.email === 'string' &&
        typeof parsed.role === 'string' &&
        typeof parsed.initials === 'string'
      ) {
        return { session: parsed as SessionUser, token };
      }
    } catch {
      // Ignore malformed storage and fall through to the login screen.
    }
  }

  return { session: null, token: null };
}

function clearStoredAuth() {
  for (const store of [window.localStorage, window.sessionStorage]) {
    try {
      store.removeItem(AUTH_TOKEN_KEY);
      store.removeItem(SESSION_STORAGE_KEY);
      store.removeItem(CHAT_SESSION_KEY);
    } catch {
      // Storage can be unavailable. In-memory state still resets.
    }
  }
}

function persistAuth(token: string, user: SessionUser, remember: boolean) {
  clearStoredAuth();
  try {
    const store = remember ? window.localStorage : window.sessionStorage;
    store.setItem(AUTH_TOKEN_KEY, token);
    store.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // The session remains valid for this tab even if persistence is blocked.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = useRef(readStoredAuth()).current;
  const [session, setSession] = useState<SessionUser | null>(initial.session);
  const [token, setToken] = useState<string | null>(initial.token);
  const [isLoading, setIsLoading] = useState(false);

  const logout = useCallback(() => {
    clearStoredAuth();
    setSession(null);
    setToken(null);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    let active = true;
    getMe(token)
      .then((user) => {
        if (active) setSession(toSessionUser(user));
      })
      .catch(() => {
        if (active) logout();
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, logout]);

  const login = useCallback(
    async (email: string, password: string, remember: boolean) => {
      try {
        const response = await apiLogin(email, password);
        const nextSession = toSessionUser(response.user);
        try {
          window.sessionStorage.removeItem(CHAT_SESSION_KEY);
        } catch {
          // Ignore storage failures.
        }
        persistAuth(response.access_token, nextSession, remember);
        setToken(response.access_token);
        setSession(nextSession);
        setIsLoading(false);
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new Error('Could not reach the Iris API. Is it running?');
      }
    },
    []
  );

  const value = useMemo(
    () => ({ session, token, isLoading, login, logout }),
    [session, token, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
