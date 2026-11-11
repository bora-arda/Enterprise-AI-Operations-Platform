import { useCallback, useMemo, useRef, useState } from 'react';
import { sendChat } from '../api/client';
import { ChatWindow } from '../components/ChatWindow';
import {
  CHAT_HISTORY_KEY_PREFIX,
  CHAT_SESSION_KEY,
} from '../config';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import type { ChatMessage, ChatSession, ChatSessionSummary } from '../types';
import { createId } from '../utils/id';

function newSessionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return createId('session');
}

function historyKey(userId: string): string {
  return `${CHAT_HISTORY_KEY_PREFIX}${userId}`;
}

function readSessions(userId: string): ChatSession[] {
  try {
    const raw = window.localStorage.getItem(historyKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatSession[];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (session) =>
          typeof session?.id === 'string' &&
          Array.isArray(session.messages) &&
          session.messages.length > 0
      )
      .sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
  } catch {
    return [];
  }
}

function persistSessions(userId: string, sessions: ChatSession[]) {
  try {
    window.localStorage.setItem(historyKey(userId), JSON.stringify(sessions));
  } catch {
    // In-memory chat state remains usable if storage is blocked.
  }
}

function titleFromMessages(messages: ChatMessage[]): string {
  const firstUser = messages.find((message) => message.role === 'user');
  if (!firstUser) return 'New conversation';
  const text = firstUser.content.replace(/\s+/g, ' ').trim();
  return text.length > 48 ? `${text.slice(0, 45)}…` : text;
}

function initialActiveSession(
  userId: string,
  sessions: ChatSession[]
): string {
  try {
    const stored = window.sessionStorage.getItem(CHAT_SESSION_KEY);
    if (stored && sessions.some((session) => session.id === stored)) {
      return stored;
    }
  } catch {
    // Fall back to the most recent session.
  }
  return sessions[0]?.id ?? newSessionId();
}

export function ChatPage() {
  const { token, session: userSession } = useAuth();
  const { showToast } = useToast();
  const userId = userSession?.id ?? 'anonymous';
  const initialSessions = useRef(readSessions(userId)).current;
  const [sessions, setSessions] = useState<ChatSession[]>(initialSessions);
  const sessionsRef = useRef<ChatSession[]>(initialSessions);
  const [activeSessionId, setActiveSessionId] = useState(() =>
    initialActiveSession(userId, initialSessions)
  );
  const [isTyping, setIsTyping] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const activeSession = sessions.find(
    (session) => session.id === activeSessionId
  );
  const messages = activeSession?.messages ?? [];

  const stopRequest = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsTyping(false);
  }, []);

  const updateSession = useCallback(
    (id: string, nextMessages: ChatMessage[]) => {
      const now = new Date().toISOString();
      const nextSession: ChatSession = {
        id,
        title: titleFromMessages(nextMessages),
        updatedAt: now,
        messages: nextMessages,
      };
      const next = [
        nextSession,
        ...sessionsRef.current.filter((session) => session.id !== id),
      ].sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
      sessionsRef.current = next;
      persistSessions(userId, next);
      setSessions(next);
      try {
        window.sessionStorage.setItem(CHAT_SESSION_KEY, id);
      } catch {
        // Ignore storage failures.
      }
    },
    [userId]
  );

  const selectSession = useCallback(
    (id: string) => {
      stopRequest();
      setActiveSessionId(id);
      try {
        window.sessionStorage.setItem(CHAT_SESSION_KEY, id);
      } catch {
        // Ignore storage failures.
      }
    },
    [stopRequest]
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || !token || isTyping) return;

      const userMessage: ChatMessage = {
        id: createId('message'),
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      };
      const baseMessages = [...messages, userMessage];
      updateSession(activeSessionId, baseMessages);
      setIsTyping(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await sendChat(
          token,
          content,
          activeSessionId,
          controller.signal
        );
        const assistantMessage: ChatMessage = {
          id: createId('message'),
          role: 'assistant',
          content: response.response,
          createdAt: new Date().toISOString(),
        };
        updateSession(activeSessionId, [...baseMessages, assistantMessage]);
      } catch (error) {
        if (controller.signal.aborted) return;
        const message =
          error instanceof Error
            ? error.message
            : 'The Iris API could not answer that request.';
        showToast({
          tone: 'error',
          title: 'Chat request failed',
          description: message,
        });
        updateSession(activeSessionId, [
          ...baseMessages,
          {
            id: createId('message'),
            role: 'assistant',
            content:
              'I could not reach the Iris API. Check that the backend is running and try again.',
            createdAt: new Date().toISOString(),
          },
        ]);
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setIsTyping(false);
        }
      }
    },
    [
      token,
      isTyping,
      messages,
      activeSessionId,
      updateSession,
      showToast,
    ]
  );

  const startNewChat = useCallback(() => {
    stopRequest();
    const nextSession = newSessionId();
    setActiveSessionId(nextSession);
    try {
      window.sessionStorage.setItem(CHAT_SESSION_KEY, nextSession);
    } catch {
      // In-memory state is still sufficient.
    }
  }, [stopRequest]);

  const history: ChatSessionSummary[] = useMemo(
    () =>
      sessions.map((session) => ({
        id: session.id,
        title: session.title,
        updatedAt: session.updatedAt,
        messageCount: session.messages.length,
      })),
    [sessions]
  );

  return (
    <div className="chat-page">
      <ChatWindow
        messages={messages}
        isTyping={isTyping}
        onSend={sendMessage}
        onNewChat={startNewChat}
        history={history}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
      />
    </div>
  );
}
