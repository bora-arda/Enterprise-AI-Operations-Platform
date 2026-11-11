import { useAuth } from '../context/AuthContext';
import type { ChatMessage } from '../types';
import { formatTime } from '../utils/format';
import { LogoMark } from './Logo';
import { MarkdownRenderer } from './MarkdownRenderer';

export function MessageBubble({ message }: { message: ChatMessage }) {
  const { session } = useAuth();
  const isAssistant = message.role === 'assistant';

  return (
    <article className={`message-row message-row--${message.role}`}>
      {isAssistant ? (
        <span className="message-avatar" aria-hidden="true">
          <LogoMark size={34} />
        </span>
      ) : (
        <span className="message-avatar message-avatar--user" aria-hidden="true">
          {session?.initials ?? 'AO'}
        </span>
      )}

      <div className="message-column">
        <div className="message-meta">
          <span className="message-meta__name">{isAssistant ? 'Iris' : 'You'}</span>
          <time dateTime={message.createdAt}>{formatTime(message.createdAt)}</time>
        </div>

        <div className={`bubble bubble--${message.role}`}>
          {isAssistant ? (
            <MarkdownRenderer content={message.content} />
          ) : (
            <p>{message.content}</p>
          )}
        </div>
      </div>
    </article>
  );
}
