/**
 * Chatbot'un tool cagrilarini gorsel olarak gosterir.
 * Particle/Notion AI tarzi "thinking" indicator.
 */

interface ToolStep {
  name: string
  label: string
  status: 'running' | 'done'
  summary?: string
}

interface ToolStepsProps {
  steps: ToolStep[]
}

export default function ToolSteps({ steps }: ToolStepsProps) {
  if (steps.length === 0) return null

  return (
    <div className="space-y-1 mb-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-text-muted">
          {step.status === 'running' ? (
            <svg
              className="w-3 h-3 animate-spin text-accent-primary flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          ) : (
            <svg
              className="w-3 h-3 text-green-500 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M5 13l4 4L19 7"
              />
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

export type { ToolStep }
