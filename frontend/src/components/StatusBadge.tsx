import type { ApprovalPriority, ApprovalStatus } from '../types';
import { Icon } from './Icons';

const STATUS_LABELS: Record<ApprovalStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
};

const STATUS_ICONS = {
  pending: 'clock',
  approved: 'check',
  rejected: 'close',
} as const;

export function StatusBadge({ status }: { status: ApprovalStatus }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      <Icon name={STATUS_ICONS[status]} size={12} />
      {STATUS_LABELS[status]}
    </span>
  );
}

const PRIORITY_LABELS: Record<ApprovalPriority, string> = {
  high: 'High priority',
  medium: 'Medium priority',
  low: 'Low priority',
};

export function PriorityTag({ priority }: { priority: ApprovalPriority }) {
  return (
    <span className={`priority priority--${priority}`} title={PRIORITY_LABELS[priority]}>
      <span className="priority__dot" aria-hidden="true" />
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}
