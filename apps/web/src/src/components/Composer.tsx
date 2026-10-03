import { useEffect, useRef, useState } from 'react'
import { ArrowUp, StopIcon } from './icons'

interface Props {
  onSend: (text: string) => void
  onStop: () => void
  streaming: boolean
  variant: 'hero' | 'docked'
  /** chips describing the active kitchen settings */
  tags?: string[]
  autoFocus?: boolean
  placeholder?: string
}

export function Composer({
  onSend,
  onStop,
  streaming,
  variant,
  tags = [],
  autoFocus,
  placeholder = 'Ask the chef — “something quick with chicken and spinach?”',
}: Props) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)

  // grow with content up to the CSS max-height
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [value])

  useEffect(() => {
    if (autoFocus) ref.current?.focus()
  }, [autoFocus])

  const submit = () => {
    const text = value.trim()
    if (!text || streaming) return
    onSend(text)
    setValue('')
  }

  return (
    <div className={`composer${focused ? ' focus' : ''}${variant === 'hero' ? ' composer-hero' : ''}`}>
      {tags.length > 0 && (
        <div className="ctags">
          {tags.map((t) => (
            <span className="tag" key={t}>
              {t}
            </span>
          ))}
        </div>
      )}

      <textarea
        ref={ref}
        value={value}
        rows={1}
        placeholder={placeholder}
        aria-label="Your question"
        onChange={(e) => setValue(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
      />

      <div className="cbar">
        {variant === 'hero' ? (
          <div className="hint">
            <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
          </div>
        ) : (
          <div className="hint" style={{ color: 'var(--faint)' }}>
            {streaming ? 'Streaming…' : 'Ask a follow-up'}
          </div>
        )}

        {streaming ? (
          <button className="btn stop" onClick={onStop} aria-label="Stop generating">
            <StopIcon width={13} height={13} />
            Stop
          </button>
        ) : (
          <button className="btn" onClick={submit} disabled={!value.trim()} aria-label="Ask the chef">
            <ArrowUp width={15} height={15} />
            {variant === 'hero' ? 'Ask the chef' : 'Send'}
          </button>
        )}
      </div>
    </div>
  )
}
