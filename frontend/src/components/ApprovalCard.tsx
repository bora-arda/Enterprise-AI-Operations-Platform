import type { Approval } from '../types';
import { formatCurrency, formatDateTime, relativeTime } from '../utils/format';
import { Icon } from './Icons';
import { PriorityTag, StatusBadge } from './StatusBadge';

interface ApprovalCardProps {
  approval: Approval;
  compact?: boolean;
  onView?: (id: string) => void;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
}

export function ApprovalCard({
  approval,
  compact = false,
  onView,
  onApprove,
  onReject,
}: ApprovalCardProps) {
  const titleId = `approval-${approval.id}-title`;

  return (
    <article
      className={compact ? 'approval-card approval-card--compact' : 'approval-card'}
      aria-labelledby={titleId}
    >
      <div className="approval-card__main">
        <div className="approval-card__topline">
          <span className="approval-card__ref">{approval.reference}</span>
          <PriorityTag priority={approval.priority} />
          <time
            className="approval-card__age"
            dateTime={approval.submittedAt}
            title={formatDateTime(approval.submittedAt)}
          >
            {relativeTime(approval.submittedAt)}
          </time>
        </div>

        <h3 className="approval-card__title" id={titleId}>
          {approval.title}
        </h3>

        <p className="approval-card__meta">
          <span>{approval.requester.name}</span>
          <span className="meta-separator" aria-hidden="true" />
          <span>{approval.category}</span>
          {!compact && (
            <>
              <span className="meta-separator" aria-hidden="true" />
              <span>{approval.requester.team}</span>
            </>
          )}
        </p>

        {!compact && <p className="approval-card__summary">{approval.summary}</p>}
      </div>

      <div className="approval-card__side">
        <p className="approval-card__amount">
          {formatCurrency(approval.amount, approval.currency)}
        </p>
        <StatusBadge status={approval.status} />

        {compact ? (
          onView && (
            <button
              type="button"
              className="icon-btn icon-btn--bordered"
              onClick={() => onView(approval.id)}
              aria-label={`View ${approval.reference}: ${approval.title}`}
              title="View details"
            >
              <Icon name="arrow-right" size={16} />
            </button>
          )
        ) : (
          <div className="approval-card__actions">
            {approval.status === 'pending' && onApprove && onReject && (
              <>
                <button
                  type="button"
                  className="btn btn--sm btn--approve"
                  onClick={() => onApprove(approval.id)}
                >
                  <Icon name="check" size={15} />
                  Approve
                </button>
                <button
                  type="button"
                  className="btn btn--sm btn--reject"
                  onClick={() => onReject(approval.id)}
                >
                  <Icon name="close" size={15} />
                  Reject
                </button>
              </>
            )}
            {onView && (
              <button
                type="button"
                className="btn btn--sm btn--secondary"
                onClick={() => onView(approval.id)}
              >
                View details
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
