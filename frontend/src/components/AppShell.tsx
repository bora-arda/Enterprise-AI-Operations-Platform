import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Icon } from './Icons';
import { Logo } from './Logo';
import { NavBar } from './NavBar';
import { ThemeToggle } from './ThemeToggle';

export function AppShell() {
  const { pathname } = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const isChat = pathname === '/chat';

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!drawerOpen) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDrawerOpen(false);
        return;
      }

      if (event.key !== 'Tab' || !drawerRef.current) return;

      const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );

      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [drawerOpen]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>

      <aside className="nav-shell nav-shell--desktop">
        <NavBar />
      </aside>

      <div className="app-frame" aria-hidden={drawerOpen || undefined}>
        <header className="mobile-bar">
          <Link to="/" className="mobile-brand" aria-label="Iris home">
            <Logo size={28} />
          </Link>
          <div className="mobile-bar__actions">
            <ThemeToggle compact />
            <button
              type="button"
              className="icon-btn icon-btn--bordered"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
              aria-expanded={drawerOpen}
              aria-controls="mobile-navigation"
            >
              <Icon name="menu" size={20} />
            </button>
          </div>
        </header>

        <main
          id="main-content"
          className={isChat ? 'app-main app-main--chat' : 'app-main'}
          tabIndex={-1}
        >
          <Outlet />
        </main>
      </div>

      {drawerOpen && (
        <div
          className="nav-scrim"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDrawerOpen(false);
          }}
        >
          <aside
            id="mobile-navigation"
            className="nav-shell nav-shell--drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Main menu"
            ref={drawerRef}
          >
            <button
              type="button"
              className="icon-btn nav-close"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close menu"
              ref={closeButtonRef}
            >
              <Icon name="close" size={20} />
            </button>
            <NavBar onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}
    </div>
  );
}
