import { useTheme } from '../context/ThemeContext';
import { Icon } from './Icons';

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, toggleTheme } = useTheme();
  const nextTheme = theme === 'light' ? 'dark' : 'light';
  const label = `Switch to ${nextTheme} theme`;

  return (
    <button
      type="button"
      className={compact ? 'theme-toggle theme-toggle--compact' : 'theme-toggle'}
      onClick={toggleTheme}
      aria-label={label}
      title={label}
    >
      <span className="theme-toggle__icon" aria-hidden="true">
        <Icon name={theme === 'light' ? 'moon' : 'sun'} size={16} />
      </span>
      {!compact && <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>}
    </button>
  );
}
