import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Icon } from './Icons';

interface ComposerProps {
  onSend: (message: string) => void;
  busy?: boolean;
}

export function Composer({ onSend, busy = false }: ComposerProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !busy;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [value]);

  const send = () => {
    const message = value.trim();
    if (!message || busy) return;
    onSend(message);
    setValue('');
    window.requestAnimationFrame(() => textareaRef.current?.focus());
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    send();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === 'Enter' &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      send();
    }
  };

  return (
    <form className="composer" onSubmit={handleSubmit} aria-label="Message composer">
      <div className="composer__box">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about an invoice, vendor, or policy…"
          aria-label="Message Iris"
          aria-describedby="composer-hint"
          rows={1}
          maxLength={4000}
        />
        <div className="composer__footer">
          <span className="composer__hint" id="composer-hint">
            {busy
              ? 'Iris is replying…'
              : 'Enter to send. Shift + Enter for a new line.'}
          </span>
          <button
            type="submit"
            className="composer__send"
            disabled={!canSend}
            aria-label="Send message"
          >
            <Icon name="send" size={16} />
            <span>Send</span>
          </button>
        </div>
      </div>
    </form>
  );
}
