import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import type { Approval } from '../types';
import { formatCurrency, formatDate, formatDateTime, relativeTime } from '../utils/format';
import { Icon } from './Icons';
import { PriorityTag, StatusBadge } from './StatusBadge';

interface ApprovalDetailPanelProps {
  approval: Approval | null;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export function ApprovalDetailPanel({
  approval,
  onClose,
  onApprove,
  onReject,
}: ApprovalDetailPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const approvalId = approval?.id;

  useEffect(() => {
    if (!approvalId) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !panelRef.current) return;

      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );

      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [approvalId, onClose]);

  // When a decision removes the footer actions, keep keyboard focus inside the
  // dialog by returning it to the close button.
  useEffect(() => {
    if (approval && approval.status !== 'pending') {
      closeButtonRef.current?.focus();
    }
  }, [approval]);

  if (!approval) return null;

  return createPortal(
    <div
      className="drawer-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        className="approval-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="approval-detail-title"
        ref={panelRef}
      >
        <header className="drawer__header">
          <div>
            <p className="panel-label">{approval.reference}</p>
            <h2 id="approval-detail-title">{approval.title}</h2>
          </div>
          <button
            type="button"
            className="icon-btn icon-btn--bordered drawer__close"
            onClick={onClose}
            aria-label="Close approval details"
            ref={closeButtonRef}
          >
            <Icon name="close" size={19} />
          </button>
        </header>

        <div className="drawer__body">
          <section className="detail-headline" aria-label="Request overview">
            <div className="detail-headline__top">
              <p className="detail-amount">
                {formatCurrency(approval.amount, approval.currency)}
              </p>
              <div className="detail-badges">
                <StatusBadge status={approval.status} />
                <PriorityTag priority={approval.priority} />
              </div>
            </div>
            <p className="detail-headline__summary">{approval.summary}</p>
          </section>

          <dl className="detail-meta">
            <div>
              <dt>Requester</dt>
              <dd>
                {approval.requester.name}
                <span className="detail-meta__sub">{approval.requester.team}</span>
              </dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{approval.category}</dd>
            </div>
            <div>
              <dt>Submitted</dt>
              <dd title={formatDateTime(approval.submittedAt)}>
                {relativeTime(approval.submittedAt)}
              </dd>
            </div>
            <div>
              <dt>Needed by</dt>
              <dd>{formatDate(approval.neededBy)}</dd>
            </div>
            <div>
              <dt>Vendor</dt>
              <dd>{approval.vendor}</dd>
            </div>
            <div>
              <dt>Cost centre</dt>
              <dd>{approval.costCenter}</dd>
            </div>
          </dl>

          <section aria-labelledby="approval-justification-heading">
            <h3 className="detail-section-title" id="approval-justification-heading">
              Justification
            </h3>
            <p className="detail-text">{approval.justification}</p>
          </section>

          <section className="policy-box" aria-labelledby="approval-policy-heading">
            <span className="policy-box__icon" aria-hidden="true">
              <Icon name="shield" size={18} />
            </span>
            <div>
              <h3 className="policy-box__title" id="approval-policy-heading">
                Policy check
              </h3>
              <p className="policy-box__text">{approval.policyNote}</p>
            </div>
          </section>

          <section aria-labelledby="approval-timeline-heading">
            <h3 className="detail-section-title" id="approval-timeline-heading">
              Activity
            </h3>
            <ol className="timeline">
              {approval.timeline.map((entry) => (
                <li key={`${entry.label}-${entry.at}`}>
                  <span className="timeline__dot" aria-hidden="true" />
                  <p className="timeline__label">{entry.label}</p>
                  <p className="timeline__detail">{entry.detail}</p>
                  <p className="timeline__time">{formatDateTime(entry.at)}</p>
                </li>
              ))}
            </ol>
          </section>
        </div>

        <footer className="drawer__footer">
          {approval.status === 'pending' ? (
            <>
              <p className="drawer__note">
                This decision is recorded by the Iris approval workflow. Payment execution remains subject to the workflow checks.
              </p>
              <div className="drawer__actions">
                <button
                  type="button"
                  className="btn btn--reject"
                  onClick={() => onReject(approval.id)}
                >
                  <Icon name="close" size={16} />
                  Reject
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => onApprove(approval.id)}
                >
                  <Icon name="check" size={16} />
                  Approve request
                </button>
              </div>
            </>
          ) : (
            <div className="drawer__decision">
              <StatusBadge status={approval.status} />
              <p>
                Decision recorded {relativeTime(
                  approval.timeline[approval.timeline.length - 1]?.at ?? approval.submittedAt
                )}
                . The decision is recorded by the Iris approval workflow.
              </p>
            </div>
          )}
        </footer>
      </aside>
    </div>,
    document.body
  );
}
