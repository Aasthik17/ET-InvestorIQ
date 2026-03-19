/**
 * useChat — State management for the Market Chat module.
 */
import { useState, useCallback, useRef } from 'react'
import { chatAPI, streamChat } from '../services/api'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [sources, setSources] = useState([])
  const [followUps, setFollowUps] = useState([])
  const abortRef = useRef(null)

  const sendMessage = useCallback(async (content, portfolio = null, useStream = true) => {
    const userMsg = { role: 'user', content, timestamp: new Date().toISOString() }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setIsStreaming(true)
    setStreamingContent('')

    const request = {
      messages: newMessages,
      portfolio,
      session_id: 'session-' + Date.now(),
    }

    if (useStream) {
      let fullContent = ''
      abortRef.current = streamChat(
        request,
        (chunk) => {
          fullContent += chunk
          setStreamingContent(fullContent)
        },
        async () => {
          // Stream done — fetch full response for sources/follow-ups
          setIsStreaming(false)
          const assistantMsg = {
            role: 'assistant',
            content: fullContent,
            timestamp: new Date().toISOString(),
          }
          setMessages(prev => [...prev, assistantMsg])
          setStreamingContent('')
        },
        (err) => {
          console.error('Stream error:', err)
          setIsStreaming(false)
          setStreamingContent('')
        }
      )
    } else {
      try {
        const response = await chatAPI.message(request)
        const assistantMsg = {
          role: 'assistant',
          content: response.response,
          sources: response.sources || [],
          tool_calls: response.tool_calls || [],
          timestamp: new Date().toISOString(),
        }
        setMessages(prev => [...prev, assistantMsg])
        setSources(response.sources || [])
        setFollowUps(response.follow_up_suggestions || [])
      } catch (err) {
        const errorMsg = {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString(),
        }
        setMessages(prev => [...prev, errorMsg])
      } finally {
        setIsStreaming(false)
      }
    }
  }, [messages])

  const clearChat = useCallback(() => {
    setMessages([])
    setSources([])
    setFollowUps([])
    setStreamingContent('')
    if (abortRef.current) abortRef.current()
  }, [])

  const stopStreaming = useCallback(() => {
    if (abortRef.current) abortRef.current()
    setIsStreaming(false)
  }, [])

  return {
    messages,
    isStreaming,
    streamingContent,
    sources,
    followUps,
    sendMessage,
    clearChat,
    stopStreaming,
  }
}
