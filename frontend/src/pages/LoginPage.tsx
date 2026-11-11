import { APP_NAME } from '../config';
import { LoginForm } from '../components/LoginForm';
import { ThemeToggle } from '../components/ThemeToggle';

export function LoginPage() {
  const year = new Date().getFullYear();

  return (
    <div className="login-page">
      <div className="login-toolbar">
        <span className="demo-chip">Live API</span>
        <ThemeToggle compact />
      </div>

      <main className="login-main" id="main-content">
        <section className="auth-card" aria-labelledby="login-heading">
          <LoginForm />
        </section>
        <p className="login-footnote">
          {APP_NAME} Procurement Operations, {year}
        </p>
      </main>
    </div>
  );
}
