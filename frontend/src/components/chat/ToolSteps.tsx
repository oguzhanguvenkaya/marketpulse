/**
 * Chatbot tool cagrilarini gorsel olarak gosterir.
 * B3: Accordion/expandable panel — sure, args, sonuc gosterimi.
 */

import { useState, useEffect } from 'react'

interface ToolStep {
  name: string
  label: string
  status: 'running' | 'done'
  summary?: string
  startTime?: number
  endTime?: number
  args?: Record<string, unknown>
}

interface ToolStepsProps {
  steps: ToolStep[]
  /** ChatPage'de detayli gosterim icin true */
  detailed?: boolean
}

/** Calisan tool icin canli sure gostergesi */
function RunningTimer({ startTime }: { startTime: number }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Date.now() - startTime)
    }, 100)
    return () => clearInterval(interval)
  }, [startTime])

  return <span className="tabular-nums">{(elapsed / 1000).toFixed(1)}s</span>
}

/** Tamamlanmis tool suresi */
function Duration({ start, end }: { start?: number; end?: number }) {
  if (!start || !end) return null
  const ms = end - start
  return <span className="tabular-nums">{(ms / 1000).toFixed(1)}s</span>
}

export default function ToolSteps({ steps, detailed = false }: ToolStepsProps) {
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set())

  if (steps.length === 0) return null

  const toggleExpand = (idx: number) => {
    setExpandedSet(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  // Basit mod — ChatPanel floating panel icin (mevcut davranis)
  if (!detailed) {
    return (
      <div className="space-y-1 mb-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-xs text-text-muted">
            {step.status === 'running' ? (
              <svg className="w-3 h-3 animate-spin text-accent-primary flex-shrink-0" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-3 h-3 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            )}
            <span className="truncate">
              {step.status === 'running' ? step.label : (step.summary || step.label.replace('...', ''))}
            </span>
          </div>
        ))}
      </div>
    )
  }

  // Detayli mod — ChatPage icin accordion
  return (
    <div className="space-y-1 mb-3">
      {steps.map((step, i) => {
        const isExpanded = expandedSet.has(i)
        const isRunning = step.status === 'running'

        return (
          <div key={i} className="rounded-lg border border-[var(--surface-border)] overflow-hidden">
            {/* Header — tiklayinca expand/collapse */}
            <button
              onClick={() => toggleExpand(i)}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-text-muted hover:bg-[var(--surface-hover)] transition-colors"
            >
              {/* Status icon */}
              {isRunning ? (
                <svg className="w-3.5 h-3.5 animate-spin text-accent-primary flex-shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              )}

              {/* Label */}
              <span className="flex-1 text-left truncate">
                {isRunning ? step.label : (step.summary || step.label.replace('...', ''))}
              </span>

              {/* Sure */}
              <span className="text-[10px] text-text-faded flex-shrink-0">
                {isRunning && step.startTime ? (
                  <RunningTimer startTime={step.startTime} />
                ) : (
                  <Duration start={step.startTime} end={step.endTime} />
                )}
              </span>

              {/* Expand icon */}
              <svg
                className={`w-3 h-3 text-text-faded transition-transform duration-200 flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Expanded content */}
            {isExpanded && (
              <div className="px-3 pb-2 pt-1 border-t border-[var(--surface-border)] bg-[var(--surface-base)] text-[11px] space-y-1.5">
                {/* Tool name */}
                <div className="flex items-center gap-2">
                  <span className="text-text-faded">Tool:</span>
                  <code className="px-1.5 py-0.5 bg-[var(--surface-hover)] rounded text-text-muted font-mono text-[10px]">
                    {step.name}
                  </code>
                </div>

                {/* Tool args */}
                {step.args && Object.keys(step.args).length > 0 && (
                  <div>
                    <span className="text-text-faded">Args:</span>
                    <pre className="mt-1 px-2 py-1.5 bg-[var(--surface-hover)] rounded text-[10px] text-text-muted overflow-x-auto font-mono">
                      {JSON.stringify(step.args, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Summary */}
                {step.summary && (
                  <div className="flex items-start gap-2">
                    <span className="text-text-faded flex-shrink-0">Sonuc:</span>
                    <span className="text-text-primary">{step.summary}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export type { ToolStep }
