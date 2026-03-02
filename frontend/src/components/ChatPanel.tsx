import { useState, useRef, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../services/client'
import { supabase } from '../lib/supabase'
import ToolSteps, { type ToolStep } from './chat/ToolSteps'
import { useChatContext } from '../hooks/useChatContext'

interface FileAttachment {
  url: string
  filename: string
  size: string
  format: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolSteps?: ToolStep[]
  files?: FileAttachment[]
  isStreaming?: boolean
  created_at?: string
}

interface Conversation {
  id: string
  title: string
  updated_at: string
}

// Custom ReactMarkdown renderer'lari — resimler, linkler ve tablolar icin
const markdownComponents = {
  img: ({ src, alt, node, ...props }: React.ImgHTMLAttributes<HTMLImageElement> & { node?: unknown }) => {
    // Tablo icindeyse kucuk thumbnail, disinda normal boyut
    // node parent kontrolu zor oldugu icin CSS ile cozuyoruz
    return (
      <img
        src={src}
        alt={alt || ''}
        loading="lazy"
        className="rounded border border-[var(--surface-border)] inline-block object-contain chat-img"
        {...props}
      />
    )
  },
  a: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[var(--accent-primary)] hover:underline break-words"
      {...props}
    >
      {children}
    </a>
  ),
  table: ({ children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) => (
    <div className="overflow-x-auto my-2 rounded-lg border border-[var(--surface-border)]">
      <table
        className="min-w-full text-[11px] border-collapse chat-table"
        {...props}
      >
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th
      className="px-2 py-1.5 bg-[var(--surface-raised)] border-b border-[var(--surface-border)] text-left font-semibold text-text-primary whitespace-nowrap text-[11px]"
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td
      className="px-2 py-1.5 border-b border-[var(--surface-border)] text-text-primary align-middle text-[11px] max-w-[150px]"
      {...props}
    >
      {children}
    </td>
  ),
  tr: ({ children, ...props }: React.HTMLAttributes<HTMLTableRowElement>) => (
    <tr
      className="hover:bg-[var(--surface-hover)] transition-colors even:bg-[var(--surface-raised)]/40"
      {...props}
    >
      {children}
    </tr>
  ),
}

export default function ChatPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Sayfa baglami ve onerilen promptlar
  const { context: pageContext, suggestions } = useChatContext()

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const loadConversations = async () => {
    try {
      const { data } = await api.get('/ai/conversations')
      setConversations(data)
    } catch {
      // Conversations endpoint may not be available yet
    }
  }

  const loadConversation = async (convId: string) => {
    try {
      const { data } = await api.get(`/ai/conversations/${convId}/messages`)
      setMessages(data)
      setConversationId(convId)
      setShowHistory(false)
    } catch {
      toast.error('Sohbet yuklenemedi')
    }
  }

  const startNewChat = () => {
    setMessages([])
    setConversationId(null)
    setShowHistory(false)
  }

  const sendMessage = async (overrideText?: string) => {
    const trimmed = (overrideText || input).trim()
    if (!trimmed || loading) return

    const userMessage: Message = { role: 'user', content: trimmed }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Bos assistant mesaji ekle — streaming dolduracak
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: '', toolSteps: [], isStreaming: true },
    ])

    try {
      // Supabase'den token al (ayni client.ts interceptor pattern'i)
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token || ''

      const response = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: trimmed,
          conversation_id: conversationId,
          page_context: pageContext,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      // Conversation ID'yi header'dan al
      const newConvId = response.headers.get('X-Conversation-Id')
      if (newConvId) setConversationId(newConvId)

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let currentEvent = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE event'lerini \n\n ile ayir
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''  // son parcayi buffer'da tut (eksik olabilir)

        for (const part of parts) {
          const lines = part.split('\n')

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                setMessages(prev => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (!last || last.role !== 'assistant') return prev

                  if (currentEvent === 'tool_start') {
                    const newStep: ToolStep = {
                      name: data.name,
                      label: data.label,
                      status: 'running',
                    }
                    return [
                      ...updated.slice(0, -1),
                      { ...last, toolSteps: [...(last.toolSteps || []), newStep] },
                    ]
                  }

                  if (currentEvent === 'tool_done') {
                    const steps = (last.toolSteps || []).map(s =>
                      s.name === data.name
                        ? { ...s, status: 'done' as const, summary: data.summary }
                        : s
                    )
                    return [...updated.slice(0, -1), { ...last, toolSteps: steps }]
                  }

                  if (currentEvent === 'token') {
                    return [
                      ...updated.slice(0, -1),
                      { ...last, content: last.content + data.content },
                    ]
                  }

                  if (currentEvent === 'file_ready') {
                    const newFile: FileAttachment = {
                      url: data.url,
                      filename: data.filename,
                      size: data.size,
                      format: data.format,
                    }
                    return [
                      ...updated.slice(0, -1),
                      { ...last, files: [...(last.files || []), newFile] },
                    ]
                  }

                  if (currentEvent === 'done') {
                    return [...updated.slice(0, -1), { ...last, isStreaming: false }]
                  }

                  if (currentEvent === 'error') {
                    return [
                      ...updated.slice(0, -1),
                      { ...last, content: data.message, isStreaming: false },
                    ]
                  }

                  return prev
                })
              } catch {
                // JSON parse hatasi — satiri atla
              }
            }
          }
        }
      }
    } catch {
      toast.error('Yanit alinamadi', { id: 'chat-error' })
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last?.role === 'assistant') {
          updated[updated.length - 1] = {
            ...last,
            content: 'Bir hata olustu. Lutfen tekrar deneyin.',
            isStreaming: false,
          }
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const togglePanel = () => {
    setIsOpen(prev => !prev)
    if (!isOpen) loadConversations()
  }

  return (
    <>
      {/* Floating Chat Button */}
      <button
        onClick={togglePanel}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-accent-primary text-white shadow-lg hover:bg-accent-primary/90 transition-all flex items-center justify-center"
        aria-label="AI Asistan"
      >
        {isOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        )}
      </button>

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-[420px] max-h-[640px] rounded-xl shadow-2xl border border-[var(--surface-border)] bg-[var(--surface-base)] flex flex-col overflow-hidden animate-fade-in">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--surface-border)] bg-[var(--surface-raised)]">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <div>
                <span className="font-semibold text-text-primary text-sm">MarketPulse AI</span>
                {pageContext && (
                  <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                    {/* Sayfa etiketi */}
                    <span className="text-[10px] text-accent-primary leading-none">
                      {pageContext.page === 'dashboard' ? 'Dashboard' :
                       pageContext.page === 'price_monitor' ? 'Fiyat Izleme' :
                       pageContext.page === 'category_explorer' ? 'Kategori Kesif' :
                       pageContext.page === 'sellers' ? 'Saticilar' :
                       pageContext.page === 'seller_detail' ? 'Satici Detay' :
                       pageContext.page === 'keyword_search' ? 'Keyword Arama' :
                       pageContext.page}
                    </span>
                    {/* Detay: kategori adi */}
                    {pageContext.category_name && (
                      <>
                        <span className="text-[10px] text-text-muted leading-none">·</span>
                        <span className="text-[10px] text-text-muted leading-none truncate max-w-[120px]" title={pageContext.category_name}>
                          {pageContext.category_name}
                        </span>
                      </>
                    )}
                    {/* Detay: urun adi */}
                    {pageContext.product_name && (
                      <>
                        <span className="text-[10px] text-text-muted leading-none">·</span>
                        <span className="text-[10px] text-text-muted leading-none truncate max-w-[120px]" title={pageContext.product_name}>
                          {pageContext.product_name}
                        </span>
                      </>
                    )}
                    {/* Keyword */}
                    {pageContext.keyword && (
                      <>
                        <span className="text-[10px] text-text-muted leading-none">·</span>
                        <span className="text-[10px] text-text-muted leading-none truncate max-w-[100px]" title={pageContext.keyword}>
                          "{pageContext.keyword}"
                        </span>
                      </>
                    )}
                    {/* Platform badge */}
                    {pageContext.platform && (
                      <span className={`text-[9px] font-medium px-1 py-0.5 rounded leading-none ${
                        pageContext.platform === 'hepsiburada'
                          ? 'bg-orange-500/15 text-orange-400'
                          : pageContext.platform === 'trendyol'
                          ? 'bg-blue-500/15 text-blue-400'
                          : 'bg-text-muted/10 text-text-muted'
                      }`}>
                        {pageContext.platform === 'hepsiburada' ? 'HB' :
                         pageContext.platform === 'trendyol' ? 'TY' :
                         pageContext.platform.toUpperCase()}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setShowHistory(!showHistory); if (!showHistory) loadConversations() }}
                className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-text-muted transition-colors"
                title="Sohbet gecmisi"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <button
                onClick={startNewChat}
                className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-text-muted transition-colors"
                title="Yeni sohbet"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>

          {/* History Panel */}
          {showHistory && (
            <div className="border-b border-[var(--surface-border)] max-h-48 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-text-muted text-xs">Henuz sohbet yok</div>
              ) : (
                conversations.map(conv => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-[var(--surface-hover)] transition-colors border-b border-[var(--surface-border)] last:border-b-0 ${conversationId === conv.id ? 'bg-accent-primary/5' : ''}`}
                  >
                    <div className="text-text-primary truncate text-xs">{conv.title}</div>
                    <div className="text-text-muted text-[10px] mt-0.5">
                      {new Date(conv.updated_at).toLocaleDateString('tr-TR')}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] max-h-[440px]">

            {/* Empty State */}
            {messages.length === 0 && (
              <div className="text-center py-6">
                <div className="w-12 h-12 rounded-full bg-accent-primary/10 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                  </svg>
                </div>
                <p className="text-text-muted text-sm font-medium">MarketPulse AI</p>
                <p className="text-text-muted text-xs mt-1">
                  Fiyat takibi, rakip analizi ve karlilik hakkinda sorun
                </p>
                {/* Sayfa bazli onerilen promptlar */}
                <div className="mt-4 space-y-2">
                  {suggestions.map(s => (
                    <button
                      key={s.text}
                      onClick={() => sendMessage(s.text)}
                      className="block w-full text-left px-3 py-2 rounded-lg bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-text-primary text-xs transition-colors"
                    >
                      {s.text}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message List */}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[90%] rounded-xl px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-accent-primary text-white'
                      : 'bg-[var(--surface-raised)] text-text-primary border border-[var(--surface-border)]'
                  }`}
                >
                  {/* Tool Steps (sadece assistant icin) */}
                  {msg.role === 'assistant' && msg.toolSteps && msg.toolSteps.length > 0 && (
                    <ToolSteps steps={msg.toolSteps} />
                  )}

                  {/* Message Content */}
                  {msg.role === 'assistant' ? (
                    <>
                      {msg.content ? (
                        <div className="prose prose-sm max-w-none text-text-primary [&_p]:mb-1 [&_ul]:mb-1 [&_li]:mb-0.5 [&_strong]:font-semibold [&_code]:bg-[var(--surface-hover)] [&_code]:px-1 [&_code]:rounded [&_table]:text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      ) : msg.isStreaming ? null : (
                        <span className="text-text-muted">...</span>
                      )}
                      {/* Dosya indirme kartlari */}
                      {msg.files && msg.files.length > 0 && (
                        <div className="mt-2 space-y-1.5">
                          {msg.files.map((file, fi) => (
                            <a
                              key={fi}
                              href={file.url}
                              download={file.filename}
                              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--surface-base)] border border-[var(--surface-border)] hover:bg-[var(--surface-hover)] transition-colors group"
                            >
                              <svg className="w-4 h-4 text-accent-primary flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-medium text-text-primary truncate group-hover:text-accent-primary">{file.filename}</div>
                                <div className="text-[10px] text-text-muted">{file.format.toUpperCase()} · {file.size}</div>
                              </div>
                              <svg className="w-3.5 h-3.5 text-text-muted group-hover:text-accent-primary flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                            </a>
                          ))}
                        </div>
                      )}
                      {/* Streaming cursor */}
                      {msg.isStreaming && msg.content && (
                        <span className="inline-block w-0.5 h-3.5 bg-accent-primary ml-0.5 animate-pulse" />
                      )}
                    </>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            ))}

            {/* Global loading (tool phase, henuz token yok) */}
            {loading && messages[messages.length - 1]?.isStreaming &&
              !messages[messages.length - 1]?.content &&
              (messages[messages.length - 1]?.toolSteps?.length ?? 0) === 0 && (
              <div className="flex justify-start">
                <div className="bg-[var(--surface-raised)] rounded-xl px-4 py-2 border border-[var(--surface-border)]">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-[var(--surface-border)] bg-[var(--surface-raised)]">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Bir soru sorun..."
                rows={1}
                disabled={loading}
                className="flex-1 resize-none rounded-lg bg-[var(--surface-base)] border border-[var(--surface-border)] px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent-primary max-h-20 disabled:opacity-60"
                style={{ minHeight: '36px' }}
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                className="p-2 rounded-lg bg-accent-primary text-white disabled:opacity-50 hover:bg-accent-primary/90 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
