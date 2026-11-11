/** Typed client for the Iris procurement API. */

export const API_BASE =
  process.env.REACT_APP_API_BASE_URL?.replace(/\/$/, '') ||
  'http://localhost:8000';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export interface ApiUser {
  id: string;
  email: string;
  name: string;
  role: string;
  department_id?: string | null;
}

export interface ApiLoginResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: ApiUser;
}

export interface ApiApproval {
  id: string;
  approval_number: string;
  request_type: string;
  invoice_id: string | null;
  invoice_number: string | null;
  amount: number | null;
  currency: string | null;
  vendor_name: string | null;
  requested_by_name: string | null;
  department_name: string | null;
  department_code: string | null;
  due_date: string | null;
  risk_level: string | null;
  status: string;
  requested_at: string | null;
  decided_at: string | null;
  justification: string | null;
}

interface ApiApprovalList {
  approvals: ApiApproval[];
  total: number;
}

export interface ApiCitation {
  source: string;
  snippet: string;
}

export interface ApiChatResponse {
  response: string;
  citations: ApiCitation[];
  confidence: number | null;
  workflow: string | null;
  trace_id: string | null;
  decision_id: string | null;
  cost_usd: number | null;
  verification_status: string | null;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let payload: unknown = null;
  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    payload = await response.json();
  }

  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === 'object' &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }

  return payload as T;
}

export function login(email: string, password: string): Promise<ApiLoginResponse> {
  return request<ApiLoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(token: string): Promise<ApiUser> {
  return request<ApiUser>('/auth/me', {}, token);
}

export function listApprovals(
  token: string,
  status?: string,
  limit = 200
): Promise<ApiApprovalList> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set('status', status);
  return request<ApiApprovalList>(`/approvals?${params.toString()}`, {}, token);
}

export function decideApproval(
  token: string,
  id: string,
  decision: 'approve' | 'reject',
  comment?: string
): Promise<ApiApproval> {
  return request<ApiApproval>(
    `/approvals/${encodeURIComponent(id)}/decide`,
    {
      method: 'POST',
      body: JSON.stringify({ decision, comment }),
    },
    token
  );
}

export function sendChat(
  token: string,
  message: string,
  sessionId: string,
  signal?: AbortSignal
): Promise<ApiChatResponse> {
  return request<ApiChatResponse>(
    '/chat',
    {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
      signal,
    },
    token
  );
}
