import type { Approval } from '../types';
import { formatCurrency, formatDateTime, relativeTime } from '../utils/format';
import { Icon } from './Icons';
import { PriorityTag, StatusBadge } from './StatusBadge';

interface ApprovalTableProps {
  approvals: Approval[];
  onView: (id: string) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export function ApprovalTable({
  approvals,
  onView,
  onApprove,
  onReject,
}: ApprovalTableProps) {
  return (
    <div className="approval-table-wrap">
      <table className="approval-table">
        <caption className="sr-only">
          Approval requests with requester, priority, amount, age, and status
        </caption>
        <thead>
          <tr>
            <th scope="col">Request</th>
            <th scope="col">Requester</th>
            <th scope="col">Priority</th>
            <th scope="col" className="numeric">
              Amount
            </th>
            <th scope="col">Submitted</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {approvals.map((approval) => {
            const titleId = `table-approval-${approval.id}-title`;
            return (
              <tr key={approval.id}>
                <td>
                  <div className="table-request">
                    <button
                      type="button"
                      className="table-request__title"
                      onClick={() => onView(approval.id)}
                      aria-describedby={titleId}
                    >
                      {approval.title}
                    </button>
                    <span className="table-request__ref" id={titleId}>
                      {approval.reference}
                    </span>
                  </div>
                </td>
                <td>
                  <div className="requester-cell">
                    <span className="avatar avatar--sm" aria-hidden="true">
                      {approval.requester.initials}
                    </span>
                    <span>
                      <span className="requester-cell__name">
                        {approval.requester.name}
                      </span>
                      <span className="requester-cell__team">
                        {approval.requester.team}
                      </span>
                    </span>
                  </div>
                </td>
                <td>
                  <PriorityTag priority={approval.priority} />
                </td>
                <td className="numeric approval-table__amount">
                  {formatCurrency(approval.amount, approval.currency)}
                </td>
                <td>
                  <time
                    dateTime={approval.submittedAt}
                    title={formatDateTime(approval.submittedAt)}
                  >
                    {relativeTime(approval.submittedAt)}
                  </time>
                </td>
                <td>
                  <StatusBadge status={approval.status} />
                </td>
                <td>
                  <div className="table-actions">
                    {approval.status === 'pending' && (
                      <>
                        <button
                          type="button"
                          className="icon-btn icon-btn--bordered icon-btn--approve"
                          onClick={() => onApprove(approval.id)}
                          aria-label={`Approve ${approval.reference}: ${approval.title}`}
                          title="Approve"
                        >
                          <Icon name="check" size={16} />
                        </button>
                        <button
                          type="button"
                          className="icon-btn icon-btn--bordered icon-btn--reject"
                          onClick={() => onReject(approval.id)}
                          aria-label={`Reject ${approval.reference}: ${approval.title}`}
                          title="Reject"
                        >
                          <Icon name="close" size={16} />
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      className="icon-btn icon-btn--bordered"
                      onClick={() => onView(approval.id)}
                      aria-label={`View ${approval.reference}: ${approval.title}`}
                      title="View details"
                    >
                      <Icon name="eye" size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
