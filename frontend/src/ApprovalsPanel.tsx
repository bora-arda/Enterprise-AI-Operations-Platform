import React, { useCallback, useEffect, useState } from 'react';

interface Approval {
  id: string;
  approval_number: string;
  request_type: string;
  invoice_id?: string | null;
  status: string;
  requested_at?: string | null;
  justification?: string | null;
}

interface Props {
  token: string;
  onUnauthorized: () => void;
}

const API_BASE = 'http://localhost:8000';

const ApprovalsPanel: React.FC<Props> = ({ token, onUnauthorized }) => {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const authHeaders = useCallback(
    () => ({
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    }),
    [token]
  );

  const loadApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/approvals?status=pending&limit=20`,
        { headers: authHeaders() }
      );
      if (response.status === 401) {
        onUnauthorized();
        return;
      }
      const data = await response.json();
      setApprovals(data.approvals || []);
    } catch {
      setMessage('Could not load approvals.');
    } finally {
      setLoading(false);
    }
  }, [authHeaders, onUnauthorized]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  const decide = async (id: string, decision: 'approve' | 'reject') => {
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/approvals/${id}/decide`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          decision,
          comment: decision === 'approve' ? 'Approved via UI' : 'Rejected via UI',
        }),
      });
      if (response.status === 401) {
        onUnauthorized();
        return;
      }
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || 'Decision failed.');
      } else {
        setMessage(
          decision === 'approve'
            ? `${data.approval_number} approved — payment executed.`
            : `${data.approval_number} rejected.`
        );
      }
      await loadApprovals();
    } catch {
      setMessage('Decision request failed.');
    }
  };

  return (
    <section className="approvals">
      <div className="approvals-header">
        <h2>Pending Approvals</h2>
        <button onClick={loadApprovals} disabled={loading}>
          Refresh
        </button>
      </div>

      {message && <div className="approvals-message">{message}</div>}

      {approvals.length === 0 && !loading && (
        <p className="approvals-empty">No pending approvals.</p>
      )}

      {approvals.map((approval) => (
        <article key={approval.id} className="approval-card">
          <div className="approval-meta">
            <strong>{approval.approval_number}</strong>
            <span>{approval.request_type}</span>
            <span className="approval-status">{approval.status}</span>
          </div>
          {approval.justification && (
            <p className="approval-justification">{approval.justification}</p>
          )}
          <div className="approval-actions">
            <button
              className="approve"
              onClick={() => decide(approval.id, 'approve')}
            >
              Approve &amp; Execute
            </button>
            <button
              className="reject"
              onClick={() => decide(approval.id, 'reject')}
            >
              Reject
            </button>
          </div>
        </article>
      ))}
    </section>
  );
};

export default ApprovalsPanel;
