import { APP_NAME } from '../config';

export function LogoMark({
  size = 30,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className={className ? `logo-mark ${className}` : 'logo-mark'}
    >
      <rect x="1" y="1" width="30" height="30" rx="9" fill="var(--accent-soft)" />
      <path
        d="M10 21.5v-11M14.4 21.5v-11M18.8 21.5v-11M23.2 21.5v-11"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
      <path
        d="M8.2 24 24.6 8"
        stroke="var(--accent)"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Logo({
  size = 32,
  subtitle,
}: {
  size?: number;
  subtitle?: string;
}) {
  return (
    <span className="logo">
      <LogoMark size={size} />
      <span className="logo__copy">
        <span className="logo__text">{APP_NAME}</span>
        {subtitle && <span className="logo__sub">{subtitle}</span>}
      </span>
    </span>
  );
}
