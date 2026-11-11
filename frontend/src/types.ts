export type ApprovalStatus = 'pending' | 'approved' | 'rejected';
export type ApprovalPriority = 'high' | 'medium' | 'low';
export type ApprovalCategory = string;

export interface Requester {
  name: string;
  team: string;
  initials: string;
}

export interface ApprovalTimelineEntry {
  label: string;
  detail: string;
  at: string;
}

export interface Approval {
  id: string;
  reference: string;
  title: string;
  summary: string;
  requester: Requester;
  amount: number;
  currency: string;
  priority: ApprovalPriority;
  status: ApprovalStatus;
  category: ApprovalCategory;
  vendor: string;
  costCenter: string;
  submittedAt: string;
  neededBy: string;
  justification: string;
  policyNote: string;
  timeline: ApprovalTimelineEntry[];
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  updatedAt: string;
  messageCount: number;
}

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  role: string;
  initials: string;
}

export type ToastTone = 'success' | 'info' | 'error';

export interface ToastMessage {
  id: string;
  tone: ToastTone;
  title: string;
  description?: string;
}
