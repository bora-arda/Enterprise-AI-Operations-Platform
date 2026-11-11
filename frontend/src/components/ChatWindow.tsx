import { useEffect, useRef, useState } from 'react';
import { STARTER_PROMPTS } from '../config';
import type { ChatMessage, ChatSessionSummary } from '../types';
import { formatDateTime } from '../utils/format';
import { Composer } from './Composer';
import { Icon } from './Icons';
import { LogoMark } from './Logo';
import { MessageBubble } from './MessageBubble';

interface ChatWindowProps {
  messages: ChatMessage[];
  isTyping: boolean;
  onSend: (message: string) => void;
  onNewChat: () => void;
  history?: ChatSessionSummary[];
  activeSessionId?: string;
  onSelectSession?: (id: string) => void;
}

function TypingIndicator() {
  return (
    <div className="message-row message-row--assistant">
      <span className="message-avatar" aria-hidden="true">
        <LogoMark size={34} />
      </span>
      <div className="typing-bubble" role="status">
        <span className="typing-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span>Iris is drafting a reply</span>
      </div>
    </div>
  );
}

export function ChatWindow({
  messages,
  isTyping,
  onSend,
  onNewChat,
  history = [],
  activeSessionId,
  onSelectSession,
}: ChatWindowProps) {
  const messagesRef = useRef<HTMLDivElement>(null);
  const historyRef = useRef<HTMLDivElement>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    if (!historyOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (
        historyRef.current &&
        !historyRef.current.contains(event.target as Node)
      ) {
        setHistoryOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setHistoryOpen(false);
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [historyOpen]);

  useEffect(() => {
    const container = messagesRef.current;
    if (!container) return;

    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches;

    const frame = window.requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: reduceMotion ? 'auto' : 'smooth',
      });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [messages.length, isTyping]);

  const isEmpty = messages.length === 0;

  return (
    <section className="chat-window" aria-labelledby="chat-title">
      <header className="chat-header">
        <div className="chat-identity">
          <LogoMark size={40} />
          <div>
            <h1 className="chat-title" id="chat-title">
              Ask Iris
            </h1>
            <p className="chat-subtitle">Procurement copilot for invoices, POs, and policy</p>
          </div>
        </div>

        <div className="chat-header__actions">
          <span className="demo-chip">Live API</span>
          <div className="chat-history-wrap" ref={historyRef}>
            <button
              type="button"
              className="btn btn--ghost btn--sm chat-history-toggle"
              onClick={() => setHistoryOpen((open) => !open)}
              aria-expanded={historyOpen}
              aria-controls="chat-history-panel"
            >
              <Icon name="clock" size={15} />
              History
              {history.length > 0 && (
                <span className="chat-history-count">{history.length}</span>
              )}
            </button>
            {historyOpen && (
              <div
                className="chat-history-panel"
                id="chat-history-panel"
                role="dialog"
                aria-label="Chat history"
              >
                <div className="chat-history-panel__head">
                  <span>Previous chats</span>
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() => setHistoryOpen(false)}
                    aria-label="Close chat history"
                  >
                    <Icon name="close" size={15} />
                  </button>
                </div>
                {history.length === 0 ? (
                  <p className="chat-history-empty">
                    Your saved conversations will appear here.
                  </p>
                ) : (
                  <div className="chat-history-list">
                    {history.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className={
                          item.id === activeSessionId
                            ? 'chat-history-item is-active'
                            : 'chat-history-item'
                        }
                        onClick={() => {
                          onSelectSession?.(item.id);
                          setHistoryOpen(false);
                        }}
                      >
                        <span className="chat-history-item__title">
                          {item.title}
                        </span>
                        <span className="chat-history-item__meta">
                          {formatDateTime(item.updatedAt)} · {item.messageCount}{' '}
                          messages
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          {(messages.length > 0 || isTyping) && (
            <button
              type="button"
              className="btn btn--ghost btn--sm chat-new"
              onClick={onNewChat}
            >
              <Icon name="plus" size={15} />
              New chat
            </button>
          )}
        </div>
      </header>

      <div
        className={isEmpty ? 'chat-messages chat-messages--empty' : 'chat-messages'}
        ref={messagesRef}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Conversation"
        aria-busy={isTyping}
      >
        {isEmpty ? (
          <div className="chat-empty">
            <span className="chat-empty__mark" aria-hidden="true">
              <LogoMark size={46} />
            </span>
            <h2>What should we look into?</h2>
            <p>
              Ask about an invoice, purchase order, vendor, or approval policy.
              Answers come from the live procurement API, with citations and verification.
            </p>
            <div className="suggestions" role="group" aria-label="Example prompts">
              <span className="suggestions__label">Try one of these</span>
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="suggestion"
                  onClick={() => onSend(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && <TypingIndicator />}
          </>
        )}
      </div>

      <Composer onSend={onSend} busy={isTyping} />
    </section>
  );
}
