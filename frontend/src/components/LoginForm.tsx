import { useRef, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { APP_TAGLINE } from '../config';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Icon } from './Icons';
import { Logo } from './Logo';

interface FormErrors {
  identifier?: string;
  password?: string;
}

function validate(identifier: string, password: string): FormErrors {
  const errors: FormErrors = {};
  const value = identifier.trim();

  if (!value) {
    errors.identifier = 'Enter your email address.';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
    errors.identifier = 'Enter a valid email address.';
  }

  if (!password) {
    errors.password = 'Enter your password.';
  } else if (password.length < 6) {
    errors.password = 'Passwords need at least 6 characters.';
  }

  return errors;
}

export function LoginForm() {
  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const identifierRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const nextErrors = validate(identifier, password);
    setErrors(nextErrors);
    setFormError(null);

    if (Object.keys(nextErrors).length > 0) {
      const target = nextErrors.identifier
        ? identifierRef.current
        : passwordRef.current;
      window.requestAnimationFrame(() => target?.focus());
      return;
    }

    setSubmitting(true);

    try {
      await login(identifier.trim(), password, remember);
      showToast({
        tone: 'success',
        title: 'Signed in',
        description: 'Connected to the Iris procurement API.',
      });
      setSubmitting(false);

      const state = location.state as { from?: string } | null;
      const destination =
        state?.from &&
        state.from.startsWith('/') &&
        !state.from.startsWith('//')
          ? state.from
          : '/';
      navigate(destination, { replace: true });
    } catch (error) {
      setFormError(
        error instanceof Error
          ? error.message
          : 'We could not sign you in. Check your details and try again.'
      );
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="auth-brand">
        <Logo size={38} />
      </div>

      <h1 className="auth-title" id="login-heading">
        Sign in to your desk.
      </h1>
      <p className="auth-sub">{APP_TAGLINE}</p>

      <form
        className="auth-form"
        onSubmit={handleSubmit}
        noValidate
        aria-labelledby="login-heading"
      >
        {formError && (
          <div className="form-error" role="alert">
            <Icon name="alert" size={17} />
            <span>{formError}</span>
          </div>
        )}

        <div className="field">
          <label htmlFor="login-identifier">Email</label>
          <div className="input-wrap">
            <span className="input-wrap__icon" aria-hidden="true">
              <Icon name="mail" size={17} />
            </span>
            <input
              ref={identifierRef}
              id="login-identifier"
              name="identifier"
              type="email"
              value={identifier}
              onChange={(event) => {
                setIdentifier(event.target.value);
                if (errors.identifier) {
                  setErrors((current) => ({ ...current, identifier: undefined }));
                }
              }}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="manager@example.com"
              aria-invalid={Boolean(errors.identifier)}
              aria-describedby={errors.identifier ? 'login-identifier-error' : undefined}
              disabled={submitting}
              autoFocus
            />
          </div>
          {errors.identifier && (
            <p className="field__error" id="login-identifier-error">
              <Icon name="alert" size={13} />
              {errors.identifier}
            </p>
          )}
        </div>

        <div className="field">
          <label htmlFor="login-password">Password</label>
          <div className="input-wrap">
            <span className="input-wrap__icon" aria-hidden="true">
              <Icon name="lock" size={17} />
            </span>
            <input
              ref={passwordRef}
              id="login-password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                if (errors.password) {
                  setErrors((current) => ({ ...current, password: undefined }));
                }
              }}
              autoComplete="current-password"
              placeholder="At least 6 characters"
              aria-invalid={Boolean(errors.password)}
              aria-describedby={
                errors.password ? 'login-password-error' : 'login-password-hint'
              }
              disabled={submitting}
            />
            <button
              type="button"
              className="icon-btn password-toggle"
              onClick={() => setShowPassword((current) => !current)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              title={showPassword ? 'Hide password' : 'Show password'}
              disabled={submitting}
            >
              <Icon name={showPassword ? 'eye-off' : 'eye'} size={18} />
            </button>
          </div>
          {errors.password ? (
            <p className="field__error" id="login-password-error">
              <Icon name="alert" size={13} />
              {errors.password}
            </p>
          ) : (
            <p className="field__hint" id="login-password-hint">
              Use at least 6 characters.
            </p>
          )}
        </div>

        <div className="form-row">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
              disabled={submitting}
            />
            <span>Remember me</span>
          </label>
        </div>

        <button
          type="submit"
          className="btn btn--primary auth-submit"
          disabled={submitting}
          aria-busy={submitting}
        >
          {submitting ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Signing in…
            </>
          ) : (
            <>
              Sign in
              <Icon name="arrow-right" size={17} />
            </>
          )}
        </button>

        <p className="auth-demo-note">
          <Icon name="shield" size={16} />
          <span>
            Demo account: <strong>manager@example.com</strong> /{' '}
            <strong>demo123</strong>. Authentication is handled by the Iris API.
          </span>
        </p>
      </form>
    </>
  );
}
