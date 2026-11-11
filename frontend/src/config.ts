/** Application-wide configuration. */

export const APP_NAME = 'Iris';
export const APP_TAGLINE = 'Procurement operations, in one clear line.';
export const APP_DESCRIPTION =
  'Review approvals, ask questions about invoices and purchase orders, and keep procurement moving.';

export const GRAFANA_URL =
  process.env.REACT_APP_GRAFANA_URL ||
  'http://localhost:3001/d/procurement-overview';

export const SESSION_STORAGE_KEY = 'iris.session';
export const AUTH_TOKEN_KEY = 'iris.token';
export const THEME_STORAGE_KEY = 'iris.theme';
export const CHAT_SESSION_KEY = 'iris.chat.session';
export const CHAT_HISTORY_KEY_PREFIX = 'iris.chats.';

export const STARTER_PROMPTS = [
  'Which invoices are overdue?',
  'Show me the top 5 invoices that exceed PO',
  'What changed in spending from 2024 to 2025?',
  'What are the approval requirements for invoices over 50000?',
];
