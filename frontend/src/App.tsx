import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ApprovalsProvider } from './context/ApprovalsContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { ChatPage } from './pages/ChatPage';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';

function ProtectedRoute() {
  const { session, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="route-loading" role="status" aria-live="polite">
        Connecting to Iris…
      </div>
    );
  }

  if (!session) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  return <Outlet />;
}

function PublicOnlyRoute() {
  const { session, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="route-loading" role="status" aria-live="polite">
        Connecting to Iris…
      </div>
    );
  }
  if (session) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<HomePage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <ApprovalsProvider>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </ApprovalsProvider>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
