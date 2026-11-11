import { Link, useNavigate } from 'react-router-dom';
import { ApprovalCard } from '../components/ApprovalCard';
import { Icon } from '../components/Icons';
import { GRAFANA_URL } from '../config';
import { useApprovals } from '../context/ApprovalsContext';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, formatLongDate, greetingForNow } from '../utils/format';

export function HomePage() {
  const { approvals, isLoading, pendingCount } = useApprovals();
  const { session } = useAuth();
  const navigate = useNavigate();

  const pending = approvals
    .filter((approval) => approval.status === 'pending')
    .sort(
      (a, b) =>
        new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime()
    );
  const latest = pending.slice(0, 3);
  const pendingValue = pending.reduce((total, approval) => total + approval.amount, 0);
  const pendingCurrencies = Array.from(
    new Set(pending.map((approval) => approval.currency))
  );
  const pendingValueText =
    pending.length === 0
      ? ''
      : pendingCurrencies.length === 1
      ? formatCurrency(pendingValue, pendingCurrencies[0])
      : `${pending.length} requests across ${pendingCurrencies.join(', ')}`;
  const firstName = session?.name.split(' ')[0] ?? 'there';
  const greeting = greetingForNow();

  return (
    <div className="page home-page">
      <header className="page-header">
        <div>
          <p className="page-kicker">{formatLongDate()}</p>
          <h1 className="page-title">
            {greeting}, {firstName}.
          </h1>
          <p className="page-lead">
            {pendingCount > 0
              ? `You have ${pendingCount} approval${
                  pendingCount === 1 ? '' : 's'
                } waiting, with ${pendingValueText} in requested spend. Start with the most recent.`
              : 'The queue is clear. Nothing needs your decision right now.'}
          </p>
        </div>
        <Link to="/approvals" className="btn btn--secondary page-header__action">
          View all approvals
          <Icon name="arrow-right" size={16} />
        </Link>
      </header>

      <div className="home-grid">
        <section
          className="panel decisions-panel"
          aria-labelledby="waiting-heading"
          aria-busy={isLoading}
        >
          <div className="section-head">
            <div>
              <h2 className="section-title" id="waiting-heading">
                Waiting on you
              </h2>
              <p className="section-sub">
                {isLoading
                  ? 'Loading the latest requests.'
                  : pendingCount > 3
                  ? `The three most recent of ${pendingCount} pending requests.`
                  : pendingCount > 0
                  ? `Showing ${pendingCount} pending request${
                      pendingCount === 1 ? '' : 's'
                    }.`
                  : 'No requests are waiting for a decision.'}
              </p>
            </div>
            {!isLoading && <span className="count-chip">{pendingCount} pending</span>}
          </div>

          {isLoading ? (
            <div className="skeleton-list" aria-label="Loading pending approvals">
              {[0, 1, 2].map((row) => (
                <div className="skeleton-approval" key={row} aria-hidden="true">
                  <div className="skeleton-approval__main">
                    <span className="skeleton-bar skeleton-bar--short" />
                    <span className="skeleton-bar skeleton-bar--title" />
                    <span className="skeleton-bar skeleton-bar--meta" />
                  </div>
                  <div className="skeleton-approval__side">
                    <span className="skeleton-bar skeleton-bar--amount" />
                    <span className="skeleton-bar skeleton-bar--badge" />
                  </div>
                </div>
              ))}
            </div>
          ) : latest.length > 0 ? (
            <div className="approval-stack">
              {latest.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  compact
                  onView={(id) => navigate(`/approvals?open=${id}`)}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-state__icon" aria-hidden="true">
                <Icon name="check" size={22} />
              </span>
              <h3>You’re all caught up.</h3>
              <p>
                New requests will appear here as soon as they are submitted. You
                can still browse past decisions.
              </p>
              <Link to="/approvals" className="link-btn">
                See past decisions
                <Icon name="arrow-right" size={15} />
              </Link>
            </div>
          )}

          <div className="section-foot">
            <Link to="/approvals" className="link-btn">
              See all approvals
              <Icon name="arrow-right" size={15} />
            </Link>
          </div>
        </section>

        <aside className="home-aside" aria-label="Shortcuts">
          <section className="panel quick-panel" aria-labelledby="shortcuts-heading">
            <h2 className="section-title" id="shortcuts-heading">
              Shortcuts
            </h2>
            <div className="quick-links">
              <Link to="/chat" className="quick-link">
                <span className="quick-link__icon" aria-hidden="true">
                  <Icon name="chat" size={19} />
                </span>
                <span className="quick-link__copy">
                  <span className="quick-link__title">Ask Iris</span>
                  <span className="quick-link__desc">
                    Check an invoice, vendor, or policy.
                  </span>
                </span>
                <Icon name="arrow-right" size={16} className="quick-link__arrow" />
              </Link>

              <a
                href={GRAFANA_URL}
                target="_blank"
                rel="noreferrer noopener"
                className="quick-link"
                aria-label="Open Grafana dashboards in a new tab"
              >
                <span className="quick-link__icon" aria-hidden="true">
                  <Icon name="chart" size={19} />
                </span>
                <span className="quick-link__copy">
                  <span className="quick-link__title">Open Grafana</span>
                  <span className="quick-link__desc">
                    Spend and throughput dashboards.
                  </span>
                </span>
                <Icon name="external" size={16} className="quick-link__arrow" />
              </a>
            </div>
          </section>

          <p className="demo-note">
            <Icon name="shield" size={17} />
            <span>
              Approvals, messages, and decisions are backed by the Iris API.
              Payment execution remains behind human approval.
            </span>
          </p>
        </aside>
      </div>
    </div>
  );
}
