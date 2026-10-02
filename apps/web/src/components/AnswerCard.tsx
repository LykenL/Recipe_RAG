import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { DonePayload, Source } from '../lib/types'
import { Book, Check, Copy, Sparkle, Warn } from './icons'

interface Props {
  content: string
  sources: Source[]
  done?: DonePayload
  error?: string
  pending: boolean
}

const LIST_LINE = /^\s*([-*+]|\d+[.)])\s+/

/**
 * Markdown requires a blank line before a list. Models routinely emit
 * "**Ingredients**\n- 2 Lbs Chicken Wings", which CommonMark renders as one
 * paragraph ("Ingredients • 2 Lbs Chicken Wings"). Inserting the missing blank
 * line is more reliable than asking the model to remember every time.
 */
function normalizeMarkdown(md: string): string {
  // Models occasionally narrate formatting instead of applying it, e.g. writing
  // the literal text "(blank line)". It is never legitimate recipe content.
  const cleaned = md.replace(/\(blank lines?\)/gi, '').replace(/[ \t]+\n/g, '\n')
  const out: string[] = []
  for (const line of cleaned.split('\n')) {
    const prev = out[out.length - 1]
    if (LIST_LINE.test(line) && prev && prev.trim() !== '' && !LIST_LINE.test(prev)) {
      out.push('')
    }
    out.push(line)
  }
  return out.join('\n')
}

/**
 * The model answers in markdown whose first line is the dish name, either as a
 * heading (`## X`) or as a bold line (`**X**`). Pulling it out lets the card use
 * the display serif for the title instead of a bold paragraph.
 */
function splitTitle(markdown: string): { title?: string; body: string; improvised: boolean } {
  let body = markdown.trim()
  let improvised = false

  // creative mode prefixes invented recipes with this exact marker
  const marker = body.match(/^_Improvised[^_]*_\s*/i)
  if (marker) {
    improvised = true
    body = body.slice(marker[0].length)
  }

  const lines = body.split('\n')
  let i = 0
  while (i < lines.length && !lines[i].trim()) i += 1

  if (i < lines.length) {
    const line = lines[i].trim()
    const candidate =
      line.match(/^#{1,4}\s+(.+)$/)?.[1] ??
      line.match(/^\*\*(.+?)\*\*:?$/)?.[1] ??
      line.match(/^__(.+?)__:?$/)?.[1]

    if (candidate && candidate.length <= 90) {
      return {
        title: candidate.replace(/[*_`]/g, '').trim(),
        body: lines.slice(i + 1).join('\n').trim(),
        improvised,
      }
    }
  }
  return { body, improvised }
}

export function AnswerCard({ content, sources, done, error, pending }: Props) {
  const [copied, setCopied] = useState(false)
  const { title, body, improvised } = splitTitle(content)
  const rendered = normalizeMarkdown(body || content)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard can be blocked; silently ignore */
    }
  }

  if (error && !content) {
    return (
      <div className="answer">
        <div className="ans-body">
          <div className="copy-error" style={{ margin: 0 }}>
            <Warn width={16} height={16} style={{ flex: 'none' }} />
            <span>{error}</span>
          </div>
        </div>
      </div>
    )
  }

  const citationLabel =
    done && done.citations > 0
      ? `Grounded in ${done.citations} source${done.citations === 1 ? '' : 's'} · every claim resolves to a citation`
      : done
        ? 'No cookbook match — answered without sources'
        : ''

  return (
    <div className="answer">
      <div className="ans-head">
        {improvised && (
          <span className="badge-improvised">
            <Sparkle width={12} height={12} /> Improvised — not from your cookbook
          </span>
        )}
        {title && <h2>{title}</h2>}
        {done && (
          <p className="ans-sub">
            {done.searches} cookbook search{done.searches === 1 ? '' : 'es'} ·{' '}
            {(done.elapsed_ms / 1000).toFixed(1)}s
          </p>
        )}
      </div>

      <div className="ans-body">
        <div className="answer-md">
          <Markdown remarkPlugins={[remarkGfm]}>{rendered}</Markdown>
          {pending && <span className="caret" />}
        </div>
      </div>

      {!pending && (
        <div className="ans-foot">
          <span>{citationLabel}</span>
          {sources.length > 0 && (
            <span className="act" title="Sources are listed in the panel">
              <Book width={12} height={12} /> {sources.length} sources
            </span>
          )}
          <span className="act" onClick={copy} role="button" tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && copy()}>
            {copied ? <Check width={12} height={12} /> : <Copy width={12} height={12} />}
            {copied ? 'Copied' : 'Copy'}
          </span>
        </div>
      )}
    </div>
  )
}
