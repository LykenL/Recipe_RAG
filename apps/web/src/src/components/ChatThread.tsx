import type { Message } from '../lib/types'
import { AgentTrace } from './AgentTrace'
import { AnswerCard } from './AnswerCard'

interface Props {
  messages: Message[]
  pantry?: string[]
}

export function ChatThread({ messages, pantry = [] }: Props) {
  return (
    <div className="thread">
      {messages.map((m) => {
        if (m.role === 'user') {
          return (
            <div className="turn-me" key={m.id}>
              <div className="bubble">{m.content}</div>
            </div>
          )
        }

        const showTrace = m.trace.length > 0 || m.pending
        return (
          <div key={m.id} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {showTrace && (
              <AgentTrace steps={m.trace} pending={Boolean(m.pending)} elapsedMs={m.done?.elapsed_ms} />
            )}
            {(m.content || m.error || !m.pending) && (
              <AnswerCard
                content={m.content}
                sources={m.sources}
                done={m.done}
                error={m.error}
                pending={Boolean(m.pending)}
                pantry={pantry}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
