/**
 * Sohbet gecmisi sidebar'i — ChatPage'in sol paneli.
 * Tarih gruplari: Bugun, Dun, Bu Hafta, Daha Eski.
 */

import type { Conversation } from '../../hooks/useChat'

interface ChatHistoryProps {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (convId: string) => void
  onDelete: (convId: string) => void
  onNewChat: () => void
}

/** Tarih grubu etiketleri */
function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)

  if (date >= today) return 'Bugun'
  if (date >= yesterday) return 'Dun'
  if (date >= weekAgo) return 'Bu Hafta'
  return 'Daha Eski'
}

/** Tarihe gore gruplama */
function groupByDate(conversations: Conversation[]): { label: string; items: Conversation[] }[] {
  const order = ['Bugun', 'Dun', 'Bu Hafta', 'Daha Eski']
  const groups = new Map<string, Conversation[]>()

  for (const conv of conversations) {
    const group = getDateGroup(conv.updated_at)
    if (!groups.has(group)) groups.set(group, [])
    groups.get(group)!.push(conv)
  }

  return order
    .filter(label => groups.has(label))
    .map(label => ({ label, items: groups.get(label)! }))
}

export default function ChatHistory({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNewChat,
}: ChatHistoryProps) {
  const grouped = groupByDate(conversations)

  return (
    <div className="flex flex-col h-full">
      {/* Yeni Sohbet butonu */}
      <div className="p-3 border-b border-[var(--surface-border)]">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-accent-primary text-white text-sm font-medium hover:bg-accent-primary/90 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Yeni Sohbet
        </button>
      </div>

      {/* Sohbet listesi */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-6 text-center">
            <div className="w-10 h-10 rounded-full bg-[var(--surface-hover)] flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-text-muted text-xs">Henuz sohbet yok</p>
            <p className="text-text-faded text-[10px] mt-1">Yeni bir sohbet baslatarak AI asistanla konusun</p>
          </div>
        ) : (
          <div className="py-2">
            {grouped.map(group => (
              <div key={group.label}>
                {/* Tarih grubu baslik */}
                <div className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-text-faded">
                  {group.label}
                </div>

                {/* Sohbet ogelerí */}
                {group.items.map(conv => (
                  <div
                    key={conv.id}
                    className={`group relative mx-2 mb-0.5 rounded-lg transition-colors cursor-pointer ${
                      activeId === conv.id
                        ? 'bg-accent-primary/10 border border-accent-primary/20'
                        : 'hover:bg-[var(--surface-hover)] border border-transparent'
                    }`}
                  >
                    <button
                      onClick={() => onSelect(conv.id)}
                      className="w-full text-left px-3 py-2.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className={`text-xs truncate leading-tight ${
                          activeId === conv.id ? 'text-accent-primary font-medium' : 'text-text-primary'
                        }`}>
                          {conv.title}
                        </span>
                        {conv.message_count && (
                          <span className="text-[9px] bg-[var(--surface-hover)] text-text-faded px-1.5 py-0.5 rounded-full flex-shrink-0">
                            {conv.message_count}
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-text-faded mt-1">
                        {new Date(conv.updated_at).toLocaleDateString('tr-TR', {
                          day: 'numeric',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </button>

                    {/* Delete — hover'da gorunur */}
                    <button
                      onClick={(e) => { e.stopPropagation(); onDelete(conv.id) }}
                      className="absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover:opacity-100 text-text-faded hover:text-red-500 hover:bg-red-500/10 transition-all"
                      title="Sohbeti sil"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
