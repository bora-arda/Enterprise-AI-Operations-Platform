import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
} from 'react';
import { useSearchParams } from 'react-router-dom';
import { ApprovalCard } from '../components/ApprovalCard';
import { ApprovalDetailPanel } from '../components/ApprovalDetailPanel';
import { ApprovalTable } from '../components/ApprovalTable';
import { Icon } from '../components/Icons';
import { useApprovals } from '../context/ApprovalsContext';
import type { ApprovalPriority, ApprovalStatus } from '../types';

type StatusFilter = 'all' | ApprovalStatus;
type PriorityFilter = 'all' | ApprovalPriority;
type SortOption = 'newest' | 'oldest' | 'amount-desc' | 'amount-asc';

const PAGE_SIZE = 6;

function ApprovalSkeleton() {
  return (
    <div className="approvals-skeleton" aria-label="Loading approvals" aria-busy="true">
      {[0, 1, 2, 3, 4, 5].map((row) => (
        <div className="skeleton-table-row" key={row} aria-hidden="true">
          <div className="skeleton-table-row__main">
            <span className="skeleton-bar skeleton-bar--title" />
            <span className="skeleton-bar skeleton-bar--meta" />
          </div>
          <span className="skeleton-bar skeleton-bar--medium" />
          <span className="skeleton-bar skeleton-bar--amount" />
          <span className="skeleton-bar skeleton-bar--badge" />
        </div>
      ))}
    </div>
  );
}

export function ApprovalsPage() {
  const { approvals, isLoading, pendingCount, decide } = useApprovals();
  const [searchParams, setSearchParams] = useSearchParams();

  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<StatusFilter>('all');
  const [priority, setPriority] = useState<PriorityFilter>('all');
  const [sort, setSort] = useState<SortOption>('newest');
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const result = approvals.filter((approval) => {
      const matchesQuery =
        !needle ||
        [
          approval.reference,
          approval.title,
          approval.summary,
          approval.requester.name,
          approval.requester.team,
          approval.vendor,
          approval.category,
        ].some((value) => value.toLowerCase().includes(needle));

      const matchesStatus = status === 'all' || approval.status === status;
      const matchesPriority = priority === 'all' || approval.priority === priority;

      return matchesQuery && matchesStatus && matchesPriority;
    });

    return result.sort((a, b) => {
      switch (sort) {
        case 'oldest':
          return (
            new Date(a.submittedAt).getTime() - new Date(b.submittedAt).getTime()
          );
        case 'amount-desc':
          return b.amount - a.amount;
        case 'amount-asc':
          return a.amount - b.amount;
        case 'newest':
        default:
          return (
            new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime()
          );
      }
    });
  }, [approvals, query, status, priority, sort]);

  useEffect(() => {
    setPage(1);
  }, [query, status, priority, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const rangeStart = filtered.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(safePage * PAGE_SIZE, filtered.length);
  const pageItems = filtered.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE
  );

  const hasFilters =
    query.trim() !== '' || status !== 'all' || priority !== 'all' || sort !== 'newest';

  const resetFilters = () => {
    setQuery('');
    setStatus('all');
    setPriority('all');
    setSort('newest');
    setPage(1);
  };

  const openId = searchParams.get('open');
  const selectedApproval = openId
    ? approvals.find((approval) => approval.id === openId) ?? null
    : null;

  const viewApproval = useCallback(
    (id: string) => {
      const next = new URLSearchParams(searchParams);
      next.set('open', id);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const closeDetails = useCallback(() => {
    const next = new URLSearchParams(searchParams);
    next.delete('open');
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  const approve = useCallback((id: string) => decide(id, 'approve'), [decide]);
  const reject = useCallback((id: string) => decide(id, 'reject'), [decide]);

  return (
    <div className="page approvals-page">
      <header className="page-header">
        <div>
          <p className="page-kicker">Procurement review queue</p>
          <h1 className="page-title">Approvals</h1>
          <p className="page-lead">
            Search the queue, filter by status, and record decisions. Your decisions are recorded by the Iris approval workflow.
          </p>
        </div>
        <span className="count-chip count-chip--large">{pendingCount} pending</span>
      </header>

      <section className="approvals-panel" aria-labelledby="approvals-list-heading">
        <h2 className="sr-only" id="approvals-list-heading">
          Approval requests
        </h2>

        <div className="approvals-toolbar">
          <div className="search-field">
            <Icon name="search" size={17} />
            <input
              type="text"
              value={query}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setQuery(event.target.value)
              }
              placeholder="Search ID, title, requester, or vendor"
              aria-label="Search approvals"
            />
            {query && (
              <button
                type="button"
                className="icon-btn search-field__clear"
                onClick={() => setQuery('')}
                aria-label="Clear search"
              >
                <Icon name="close" size={15} />
              </button>
            )}
          </div>

          <div className="filter-row">
            <div className="select-wrap">
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value as StatusFilter)}
                aria-label="Filter by status"
              >
                <option value="all">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
              <Icon name="chevron-down" size={15} />
            </div>

            <div className="select-wrap">
              <select
                value={priority}
                onChange={(event) => setPriority(event.target.value as PriorityFilter)}
                aria-label="Filter by priority"
              >
                <option value="all">All priorities</option>
                <option value="high">High priority</option>
                <option value="medium">Medium priority</option>
                <option value="low">Low priority</option>
              </select>
              <Icon name="chevron-down" size={15} />
            </div>

            <div className="select-wrap">
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as SortOption)}
                aria-label="Sort approvals"
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="amount-desc">Amount: high to low</option>
                <option value="amount-asc">Amount: low to high</option>
              </select>
              <Icon name="arrow-up-down" size={15} />
            </div>
          </div>
        </div>

        <div className="results-line">
          <p aria-live="polite">
            {isLoading
              ? 'Loading approvals…'
              : filtered.length === 0
              ? 'No requests match the current filters'
              : `Showing ${rangeStart}–${rangeEnd} of ${filtered.length} requests`}
          </p>
          {hasFilters && (
            <button type="button" className="link-btn" onClick={resetFilters}>
              <Icon name="refresh" size={14} />
              Clear filters
            </button>
          )}
        </div>

        {isLoading ? (
          <ApprovalSkeleton />
        ) : filtered.length === 0 ? (
          <div className="empty-state approvals-empty">
            <span className="empty-state__icon" aria-hidden="true">
              <Icon name="inbox" size={22} />
            </span>
            <h3>
              {approvals.length === 0
                ? 'No approvals yet.'
                : 'No approvals match those filters.'}
            </h3>
            <p>
              {approvals.length === 0
                ? 'Requests will appear here once they are submitted.'
                : 'Try a different status, priority, or search term.'}
            </p>
            {hasFilters && (
              <button type="button" className="btn btn--secondary btn--sm" onClick={resetFilters}>
                <Icon name="refresh" size={15} />
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <>
            <ApprovalTable
              approvals={pageItems}
              onView={viewApproval}
              onApprove={approve}
              onReject={reject}
            />

            <div className="approvals-cards">
              {pageItems.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  onView={viewApproval}
                  onApprove={approve}
                  onReject={reject}
                />
              ))}
            </div>

            {totalPages > 1 && (
              <nav className="pagination" aria-label="Approval pages">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setPage(Math.max(1, safePage - 1))}
                  disabled={safePage === 1}
                >
                  <Icon name="chevron-left" size={15} />
                  Previous
                </button>

                <div className="pagination__pages">
                  {Array.from({ length: totalPages }, (_, index) => index + 1).map(
                    (pageNumber) => (
                      <button
                        key={pageNumber}
                        type="button"
                        className="page-btn"
                        onClick={() => setPage(pageNumber)}
                        aria-label={`Page ${pageNumber}`}
                        aria-current={pageNumber === safePage ? 'page' : undefined}
                      >
                        {pageNumber}
                      </button>
                    )
                  )}
                </div>

                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setPage(Math.min(totalPages, safePage + 1))}
                  disabled={safePage === totalPages}
                >
                  Next
                  <Icon name="chevron-right" size={15} />
                </button>
              </nav>
            )}
          </>
        )}
      </section>

      <ApprovalDetailPanel
        approval={selectedApproval}
        onClose={closeDetails}
        onApprove={approve}
        onReject={reject}
      />
    </div>
  );
}
