/**
 * Tam sayfa AI Chat deneyimi — 3 panelli layout.
 * Sol: Sohbet gecmisi | Orta: Chat alani | Search scope toggle.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import type { Message } from '../hooks/useChat'
import ToolSteps from '../components/chat/ToolSteps'
import ChatHistory from '../components/chat/ChatHistory'
import { markdownComponents } from '../components/chat/markdownComponents'

/** Search scope badge gosterimi */
function SearchScopeBadge({
  scope,
  onCycle,
}: {
  scope: 'auto' | 'page' | 'global'
  onCycle: () => void
}) {
  const config = {
    auto: { icon: '🔄', label: 'Otomatik', color: 'text-text-muted bg-[var(--surface-hover)]' },
    page: { icon: '📍', label: 'Sayfa', color: 'text-accent-primary bg-accent-primary/10' },
    global: { icon: '🌐', label: 'Tumu', color: 'text-blue-400 bg-blue-500/10' },
  }
  const c = config[scope]

  return (
    <button
      onClick={onCycle}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors hover:opacity-80 ${c.color}`}
      title="Arama kapsamini degistir"
    >
      <span className="text-xs">{c.icon}</span>
      {c.label}
    </button>
  )
}

/** Dosya indirme karti */
function FileCard({ file }: { file: { url: string; filename: string; size: string; format: string } }) {
  return (
    <a
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
  )
}

/** Tek mesaj rendereri */
function ChatMessage({ msg, isDetailed }: { msg: Message; isDetailed: boolean }) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? 'bg-accent-primary text-white'
            : 'bg-[var(--surface-raised)] text-text-primary border border-[var(--surface-border)]'
        }`}
      >
        {/* Tool Steps */}
        {!isUser && msg.toolSteps && msg.toolSteps.length > 0 && (
          <ToolSteps steps={msg.toolSteps} detailed={isDetailed} />
        )}

        {/* Content */}
        {isUser ? (
          <span className="whitespace-pre-wrap">{msg.content}</span>
        ) : (
          <>
            {msg.content ? (
              <div className="prose prose-sm max-w-none text-text-primary [&_p]:mb-1.5 [&_ul]:mb-1 [&_li]:mb-0.5 [&_strong]:font-semibold [&_code]:bg-[var(--surface-hover)] [&_code]:px-1 [&_code]:rounded [&_table]:text-xs [&_h3]:text-sm [&_h3]:mt-3 [&_h3]:mb-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            ) : msg.isStreaming ? null : (
              <span className="text-text-muted">...</span>
            )}

            {/* Dosya kartlari */}
            {msg.files && msg.files.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {msg.files.map((file, fi) => <FileCard key={fi} file={file} />)}
              </div>
            )}

            {/* Streaming cursor */}
            {msg.isStreaming && msg.content && (
              <span className="inline-block w-0.5 h-3.5 bg-accent-primary ml-0.5 animate-pulse" />
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function ChatPage() {
  const {
    messages,
    input,
    setInput,
    loading,
    conversationId,
    conversations,
    searchScope,
    cycleSearchScope,
    suggestions,
    loadConversations,
    loadConversation,
    deleteConversation,
    startNewChat,
    sendMessage,
  } = useChat()

  const [historyOpen, setHistoryOpen] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleSelectConversation = (convId: string) => {
    loadConversation(convId)
  }

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* Sol panel — Sohbet gecmisi */}
      <aside
        className={`${
          historyOpen ? 'w-[280px]' : 'w-0'
        } flex-shrink-0 border-r border-[var(--surface-border)] bg-[var(--surface-base)] transition-all duration-300 overflow-hidden`}
      >
        <ChatHistory
          conversations={conversations}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onDelete={deleteConversation}
          onNewChat={startNewChat}
        />
      </aside>

      {/* Orta panel — Chat alani */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--surface-border)] bg-[var(--surface-raised)]">
          <div className="flex items-center gap-3">
            {/* History toggle */}
            <button
              onClick={() => setHistoryOpen(prev => !prev)}
              className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-text-muted transition-colors"
              title={historyOpen ? 'Gecmisi gizle' : 'Gecmisi goster'}
            >
              <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
              </svg>
            </button>

            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-accent-primary/10 flex items-center justify-center">
                <svg className="w-3.5 h-3.5 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <span className="font-semibold text-text-primary text-sm">MarketPulse AI</span>
            </div>
          </div>

          <button
            onClick={() => { startNewChat(); inputRef.current?.focus() }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-text-muted hover:text-accent-primary hover:bg-accent-primary/10 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Yeni Sohbet
          </button>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-4 space-y-4">
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full max-w-lg mx-auto">
              <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <h2 className="text-lg font-bold text-text-primary mb-1">MarketPulse AI</h2>
              <p className="text-text-muted text-sm mb-6 text-center">
                Fiyat takibi, rakip analizi ve karlilik hakkinda sorun.
                Verileriniz uzerinden akilli analizler yapar.
              </p>

              {/* Onerilen promptlar */}
              <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-2">
                {suggestions.map(s => (
                  <button
                    key={s.text}
                    onClick={() => sendMessage(s.text)}
                    className="text-left px-4 py-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--surface-border)] hover:border-accent-primary/30 hover:bg-[var(--surface-hover)] text-text-primary text-xs transition-all"
                  >
                    {s.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg, i) => (
            <ChatMessage key={i} msg={msg} isDetailed={true} />
          ))}

          {/* Loading dots — streaming basladi ama henuz icerik yok */}
          {loading && messages[messages.length - 1]?.isStreaming &&
            !messages[messages.length - 1]?.content &&
            (messages[messages.length - 1]?.toolSteps?.length ?? 0) === 0 && (
            <div className="flex justify-start">
              <div className="bg-[var(--surface-raised)] rounded-2xl px-5 py-3 border border-[var(--surface-border)]">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area — sticky bottom */}
        <div className="border-t border-[var(--surface-border)] bg-[var(--surface-raised)] px-4 md:px-8 py-3">
          {/* Search scope toggle */}
          <div className="flex items-center justify-between mb-2">
            <SearchScopeBadge scope={searchScope} onCycle={cycleSearchScope} />
          </div>

          <div className="flex items-end gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Bir soru sorun..."
              rows={1}
              disabled={loading}
              className="flex-1 resize-none rounded-xl bg-[var(--surface-base)] border border-[var(--surface-border)] px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary/50 max-h-32 disabled:opacity-60 transition-all"
              style={{ minHeight: '44px' }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              className="p-3 rounded-xl bg-accent-primary text-white disabled:opacity-50 hover:bg-accent-primary/90 transition-colors flex-shrink-0"
            >
              <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
