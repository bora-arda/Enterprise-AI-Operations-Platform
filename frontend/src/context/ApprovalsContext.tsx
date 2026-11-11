import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  ApiError,
  decideApproval,
  listApprovals,
} from '../api/client';
import { toApproval } from '../api/adapters';
import type { Approval } from '../types';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

type Decision = 'approve' | 'reject';

interface ApprovalsContextValue {
  approvals: Approval[];
  isLoading: boolean;
  pendingCount: number;
  decide: (id: string, decision: Decision) => Promise<void>;
}

const ApprovalsContext = createContext<ApprovalsContextValue | null>(null);

export function ApprovalsProvider({ children }: { children: ReactNode }) {
  const { token, logout } = useAuth();
  const { showToast } = useToast();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [isLoading, setIsLoading] = useState(Boolean(token));

  const loadApprovals = useCallback(async () => {
    if (!token) {
      setApprovals([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await listApprovals(token);
      setApprovals(response.approvals.map(toApproval));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        logout();
      } else {
        showToast({
          tone: 'error',
          title: 'Could not load approvals',
          description:
            error instanceof Error ? error.message : 'The approvals API is unavailable.',
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [token, logout, showToast]);

  useEffect(() => {
    void loadApprovals();
  }, [loadApprovals]);

  const decide = useCallback(
    async (id: string, decision: Decision) => {
      if (!token) return;
      const target = approvals.find(
        (approval) => approval.id === id && approval.status === 'pending'
      );
      if (!target) return;

      try {
        await decideApproval(
          token,
          id,
          decision,
          decision === 'approve'
            ? 'Approved from the Iris review desk.'
            : 'Rejected from the Iris review desk.'
        );
        showToast({
          tone: decision === 'approve' ? 'success' : 'info',
          title: `${target.reference} ${
            decision === 'approve' ? 'approved' : 'rejected'
          }`,
          description:
            decision === 'approve'
              ? 'The approval was recorded. Payment execution remains subject to the workflow checks.'
              : 'The rejection was recorded by the approval workflow.',
        });
        await loadApprovals();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          logout();
          return;
        }
        showToast({
          tone: 'error',
          title: 'Decision failed',
          description:
            error instanceof Error
              ? error.message
              : 'The approval decision could not be recorded.',
        });
      }
    },
    [approvals, token, showToast, loadApprovals, logout]
  );

  const pendingCount = useMemo(
    () => approvals.filter((approval) => approval.status === 'pending').length,
    [approvals]
  );

  const value = useMemo(
    () => ({ approvals, isLoading, pendingCount, decide }),
    [approvals, isLoading, pendingCount, decide]
  );

  return (
    <ApprovalsContext.Provider value={value}>
      {children}
    </ApprovalsContext.Provider>
  );
}

export function useApprovals(): ApprovalsContextValue {
  const context = useContext(ApprovalsContext);
  if (!context) {
    throw new Error('useApprovals must be used inside ApprovalsProvider');
  }
  return context;
}
