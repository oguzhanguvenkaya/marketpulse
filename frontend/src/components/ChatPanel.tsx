/**
 * Floating chat panel — diger sayfalarda gorunur, /chat route'unda gizlenir.
 * B5: useChat hook kullanimi + route check.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import ToolSteps from './chat/ToolSteps'
import { markdownComponents } from './chat/markdownComponents'

export default function ChatPanel() {
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    input,
    setInput,
    loading,
    conversationId,
    conversations,
    pageContext,
    suggestions,
    loadConversations,
    loadConversation,
    startNewChat,
    sendMessage,
  } = useChat()

  // Auto-scroll mesajlar degisince
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

  const handleLoadConversation = (convId: string) => {
    loadConversation(convId)
    setShowHistory(false)
  }

  const handleStartNewChat = () => {
    startNewChat()
    setShowHistory(false)
  }

  // /chat route'unda floating panel'i gizle
  if (location.pathname === '/chat') return null

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
                    <span className="text-[10px] text-accent-primary leading-none">
                      {pageContext.page === 'dashboard' ? 'Dashboard' :
                       pageContext.page === 'price_monitor' ? 'Fiyat Izleme' :
                       pageContext.page === 'category_explorer' ? 'Kategori Kesif' :
                       pageContext.page === 'sellers' ? 'Saticilar' :
                       pageContext.page === 'seller_detail' ? 'Satici Detay' :
                       pageContext.page === 'keyword_search' ? 'Keyword Arama' :
                       pageContext.page}
                    </span>
                    {pageContext.category_name && (
                      <>
                        <span className="text-[10px] text-text-muted leading-none">·</span>
                        <span className="text-[10px] text-text-muted leading-none truncate max-w-[120px]" title={pageContext.category_name}>
                          {pageContext.category_name}
                        </span>
                      </>
                    )}
                    {pageContext.product_name && (
                      <>
                        <span className="text-[10px] text-text-muted leading-none">·</span>
                        <span className="text-[10px] text-text-muted leading-none truncate max-w-[120px]" title={pageContext.product_name}>
                          {pageContext.product_name}
                        </span>
                      </>
                    )}
                    {pageContext.keyword && (
                      <>
                        <span className="text-[10px] text-text-muted leading-none">·</span>
                        <span className="text-[10px] text-text-muted leading-none truncate max-w-[100px]" title={pageContext.keyword}>
                          "{pageContext.keyword}"
                        </span>
                      </>
                    )}
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
                onClick={handleStartNewChat}
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
                    onClick={() => handleLoadConversation(conv.id)}
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
                  {msg.role === 'assistant' && msg.toolSteps && msg.toolSteps.length > 0 && (
                    <ToolSteps steps={msg.toolSteps} />
                  )}

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

            {/* Loading dots */}
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
