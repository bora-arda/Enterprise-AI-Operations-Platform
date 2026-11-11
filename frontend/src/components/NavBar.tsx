import { Link, NavLink, useNavigate } from 'react-router-dom';
import { GRAFANA_URL } from '../config';
import { useApprovals } from '../context/ApprovalsContext';
import { useAuth } from '../context/AuthContext';
import { Icon } from './Icons';
import { Logo } from './Logo';
import { ThemeToggle } from './ThemeToggle';

interface NavBarProps {
  onNavigate?: () => void;
}

function navLinkClass({ isActive }: { isActive: boolean }) {
  return isActive ? 'nav-link is-active' : 'nav-link';
}

export function NavBar({ onNavigate }: NavBarProps) {
  const { session, logout } = useAuth();
  const { pendingCount } = useApprovals();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    onNavigate?.();
    navigate('/login', { replace: true });
  };

  return (
    <div className="nav-inner">
      <Link
        to="/"
        className="brand"
        aria-label="Iris home"
        onClick={onNavigate}
      >
        <Logo subtitle="Procurement operations" />
      </Link>

      <nav className="nav-links" aria-label="Main">
        <NavLink to="/" end className={navLinkClass} onClick={onNavigate}>
          <Icon name="home" size={19} />
          <span>Home</span>
        </NavLink>

        <NavLink
          to="/approvals"
          className={navLinkClass}
          onClick={onNavigate}
          aria-label={
            pendingCount > 0
              ? `Pending approvals, ${pendingCount} waiting`
              : 'Pending approvals'
          }
        >
          <Icon name="approvals" size={19} />
          <span>Pending approvals</span>
          {pendingCount > 0 && (
            <span className="nav-badge" aria-hidden="true">
              {pendingCount}
            </span>
          )}
        </NavLink>

        <NavLink to="/chat" className={navLinkClass} onClick={onNavigate}>
          <Icon name="chat" size={19} />
          <span>Chat</span>
        </NavLink>

        <a
          href={GRAFANA_URL}
          target="_blank"
          rel="noreferrer noopener"
          className="nav-link nav-link--external"
          onClick={onNavigate}
          aria-label="Open Grafana dashboards in a new tab"
        >
          <Icon name="chart" size={19} />
          <span>Grafana</span>
          <Icon name="external" size={14} className="nav-external-icon" />
        </a>
      </nav>

      <div className="nav-footer">
        <div className="theme-row">
          <span className="theme-row__label">Appearance</span>
          <ThemeToggle compact />
        </div>

        <div className="user-card">
          <span className="avatar" aria-hidden="true">
            {session?.initials ?? 'AO'}
          </span>
          <span className="user-copy">
            <span className="user-name">{session?.name ?? 'Amara Okafor'}</span>
            <span className="user-role">{session?.role ?? 'Procurement manager'}</span>
          </span>
          <button
            type="button"
            className="icon-btn"
            onClick={handleLogout}
            aria-label="Sign out"
            title="Sign out"
          >
            <Icon name="logout" size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
