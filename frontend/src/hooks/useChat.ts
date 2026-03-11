/**
 * Chatbot state ve SSE streaming mantigi.
 * ChatPanel (floating) ve ChatPage (tam sayfa) tarafindan paylasilan hook.
 */

import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { api } from '../services/client'
import { supabase } from '../lib/supabase'
import { useChatContext } from './useChatContext'
import type { ToolStep } from '../components/chat/ToolSteps'

// --- Types ---

export interface FileAttachment {
  url: string
  filename: string
  size: string
  format: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  toolSteps?: ToolStep[]
  files?: FileAttachment[]
  isStreaming?: boolean
  created_at?: string
}

export interface Conversation {
  id: string
  title: string
  updated_at: string
  message_count?: number
}

export type SearchScope = 'auto' | 'page' | 'global'

// --- Hook ---

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [searchScope, setSearchScope] = useState<SearchScope>('auto')

  const { context: pageContext, suggestions } = useChatContext()

  const loadConversations = useCallback(async () => {
    try {
      const { data } = await api.get('/ai/conversations')
      setConversations(data)
    } catch {
      // endpoint may not be available yet
    }
  }, [])

  const loadConversation = useCallback(async (convId: string) => {
    try {
      const { data } = await api.get(`/ai/conversations/${convId}/messages`)
      setMessages(data)
      setConversationId(convId)
    } catch {
      toast.error('Sohbet yuklenemedi')
    }
  }, [])

  const deleteConversation = useCallback(async (convId: string) => {
    try {
      await api.delete(`/ai/conversations/${convId}`)
      setConversations(prev => prev.filter(c => c.id !== convId))
      setConversationId(prev => {
        if (prev === convId) {
          setMessages([])
          return null
        }
        return prev
      })
      toast.success('Sohbet silindi')
    } catch {
      toast.error('Sohbet silinemedi')
    }
  }, [])

  const startNewChat = useCallback(() => {
    setMessages([])
    setConversationId(null)
  }, [])

  const sendMessage = useCallback(async (overrideText?: string) => {
    const trimmed = (overrideText || input).trim()
    if (!trimmed || loading) return

    const userMessage: Message = { role: 'user', content: trimmed }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Bos assistant mesaji — streaming dolduracak
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: '', toolSteps: [], isStreaming: true },
    ])

    try {
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
          ...(searchScope !== 'auto' && { search_scope: searchScope }),
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

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

        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

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
                      startTime: Date.now(),
                      ...(data.args && { args: data.args }),
                    }
                    return [
                      ...updated.slice(0, -1),
                      { ...last, toolSteps: [...(last.toolSteps || []), newStep] },
                    ]
                  }

                  if (currentEvent === 'tool_done') {
                    const steps = (last.toolSteps || []).map(s =>
                      s.name === data.name
                        ? { ...s, status: 'done' as const, summary: data.summary, endTime: Date.now() }
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
  }, [input, loading, conversationId, pageContext, searchScope])

  const cycleSearchScope = useCallback(() => {
    setSearchScope(prev =>
      prev === 'auto' ? 'page' : prev === 'page' ? 'global' : 'auto'
    )
  }, [])

  return {
    // State
    messages,
    input,
    setInput,
    loading,
    conversationId,
    conversations,
    searchScope,
    pageContext,
    suggestions,
    // Actions
    loadConversations,
    loadConversation,
    deleteConversation,
    startNewChat,
    sendMessage,
    cycleSearchScope,
  }
}
