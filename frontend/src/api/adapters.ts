import type { ApiApproval } from '../api/client';
import type { Approval, ApprovalPriority, ApprovalStatus } from '../types';
import { initialsFromName } from '../utils/format';

const STATUSES: ApprovalStatus[] = ['pending', 'approved', 'rejected'];

function statusFromApi(value: string): ApprovalStatus {
  return STATUSES.includes(value as ApprovalStatus)
    ? (value as ApprovalStatus)
    : 'pending';
}

function priorityFromApi(value: string | null, amount: number): ApprovalPriority {
  if (value === 'high' || value === 'medium' || value === 'low') {
    return value;
  }
  if (amount >= 50_000) return 'high';
  if (amount >= 10_000) return 'medium';
  return 'low';
}

/** Adapt the API approval row to the presentational approval model. */
export function toApproval(dto: ApiApproval): Approval {
  const amount = dto.amount ?? 0;
  const currency = dto.currency || 'GBP';
  const status = statusFromApi(dto.status);
  const requestLabel =
    dto.request_type === 'payment_request'
      ? 'Payment request'
      : 'Invoice approval';
  const submittedAt = dto.requested_at || new Date().toISOString();
  const requesterName = dto.requested_by_name || 'Approval workflow';
  const team = dto.department_name || 'Procurement';
  const reference = dto.invoice_number || dto.approval_number;
  const priority = priorityFromApi(dto.risk_level, amount);
  const timeline = [
    {
      label: `${requestLabel} raised`,
      detail: `${requesterName} submitted this request for review.`,
      at: submittedAt,
    },
  ];

  if (dto.decided_at) {
    timeline.push({
      label: status === 'approved' ? 'Approved' : 'Rejected',
      detail: `Decision recorded by the Iris approval workflow.`,
      at: dto.decided_at,
    });
  }

  return {
    id: dto.id,
    reference: dto.approval_number,
    title: `${requestLabel} · ${reference}`,
    summary: dto.justification || `${requestLabel} awaiting review.`,
    requester: {
      name: requesterName,
      team,
      initials: initialsFromName(requesterName) || 'AW',
    },
    amount,
    currency,
    priority,
    status,
    category: requestLabel,
    vendor: dto.vendor_name || 'Unknown vendor',
    costCenter: dto.department_code
      ? `${dto.department_code} · ${team}`
      : team,
    submittedAt,
    neededBy: dto.due_date || submittedAt,
    justification: dto.justification || 'No justification was recorded.',
    policyNote:
      'This request is managed by the Iris approval workflow. Payment execution remains blocked until a human decision is recorded.',
    timeline,
  };
}
