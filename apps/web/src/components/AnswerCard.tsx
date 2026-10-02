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
/** Models like to emit a literal bullet glyph instead of markdown "- ". */
const BULLET_GLYPH = /^\s*[•·‣▪●]\s*/

/**
 * Make model output render predictably. Two real failure modes seen in
 * production, both of which are more reliably fixed here than by asking the
 * model to remember:
 *
 *   1. "**Ingredients**\n- item" — no blank line before a list, so CommonMark
 *      renders one paragraph ("Ingredients • 2 Lbs Chicken Wings").
 *   2. "• item" — a literal bullet glyph is not a list marker to CommonMark.
 *   3. "(blank line)" — narrating formatting instead of applying it.
 */
function normalizeMarkdown(md: string): string {
  const cleaned = md.replace(/\(blank lines?\)/gi, '').replace(/[ \t]+$/gm, '')
  const out: string[] = []

  for (const raw of cleaned.split('\n')) {
    const line = BULLET_GLYPH.test(raw) ? raw.replace(BULLET_GLYPH, '- ') : raw
    const prev = out[out.length - 1]
    if (LIST_LINE.test(line) && prev && prev.trim() !== '' && !LIST_LINE.test(prev)) {
      out.push('')
    }
    out.push(line)
  }
  return out.join('\n')
}

/**
 * The dish name is usually the first line, as a heading (`## X`), a bold line
 * (`**X**`), or — when the model ignores both — a bare short line immediately
 * followed by the ingredient list. Lifting it out lets the card set the title in
 * the display serif rather than as a bold paragraph.
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
    const explicit =
      line.match(/^#{1,4}\s+(.+)$/)?.[1] ??
      line.match(/^\*\*(.+?)\*\*:?$/)?.[1] ??
      line.match(/^__(.+?)__:?$/)?.[1]

    // bare title heuristic: short line, no terminal punctuation, list follows.
    // Skip intervening blank lines — normalisation inserts one before the list.
    let j = i + 1
    while (j < lines.length && !lines[j].trim()) j += 1
    const next = lines[j]?.trim() ?? ''
    const bare =
      !explicit && line.length <= 70 && !/[.:;!?]$/.test(line) && LIST_LINE.test(next)
        ? line
        : undefined

    const candidate = explicit ?? bare
    if (candidate) {
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
  const { title, body, improvised } = splitTitle(normalizeMarkdown(content))
  const rendered = body

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard can be blocked; silently ignore */
    }
  }

  if ((error || !content.trim()) && !pending) {
    // An empty answer with real sources is worse than an error: the footer would
    // claim "grounded in N sources" over a blank card. Say what happened instead.
    return (
      <div className="answer">
        <div className="ans-body">
          <div className="copy-error" style={{ margin: 0 }}>
            <Warn width={16} height={16} style={{ flex: 'none' }} />
            <span>
              {error ??
                'The model returned no answer this time. This usually means it used its whole budget on internal reasoning — ask again, or rephrase the question.'}
            </span>
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
