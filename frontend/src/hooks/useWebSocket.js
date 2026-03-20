import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * WebSocket hook with auto-reconnect and exponential backoff.
 *
 * @param {string|null} path - WS path e.g. '/ws/prices'. Pass null to disable.
 * @returns {{ data, status, reconnect }}
 *   data:   latest parsed JSON message from the socket
 *   status: 'connecting' | 'open' | 'closed' | 'error'
 *   reconnect: () => void  — manual reconnect trigger
 */
export function useWebSocket(path) {
  const [data,   setData]   = useState(null)
  const [status, setStatus] = useState('connecting')

  const wsRef          = useRef(null)
  const reconnectTimer = useRef(null)
  const retryCount     = useRef(0)
  const isMounted      = useRef(true)

  const connect = useCallback(() => {
    if (!path || !isMounted.current) return

    // Build URL: ws(s)://host/path
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // In development, Vite proxies /ws → ws://localhost:8000
    const host  = import.meta.env.VITE_API_WS_URL
      || (window.location.host)
    const url = `${proto}//${host}${path}`

    try {
      wsRef.current = new WebSocket(url)
    } catch (e) {
      setStatus('error')
      scheduleReconnect()
      return
    }

    setStatus('connecting')

    wsRef.current.onopen = () => {
      if (!isMounted.current) return
      setStatus('open')
      retryCount.current = 0  // Reset backoff on successful connection
    }

    wsRef.current.onmessage = (e) => {
      if (!isMounted.current) return
      try {
        setData(JSON.parse(e.data))
      } catch {
        // Ignore malformed messages
      }
    }

    wsRef.current.onerror = () => {
      if (!isMounted.current) return
      setStatus('error')
    }

    wsRef.current.onclose = () => {
      if (!isMounted.current) return
      setStatus('closed')
      scheduleReconnect()
    }
  }, [path])  // eslint-disable-line react-hooks/exhaustive-deps

  const scheduleReconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current)
    if (!isMounted.current) return
    // Exponential backoff: 1s, 2s, 4s, 8s, max 15s
    const delay = Math.min(1000 * Math.pow(2, retryCount.current), 15_000)
    retryCount.current += 1
    reconnectTimer.current = setTimeout(connect, delay)
  }, [connect])

  useEffect(() => {
    isMounted.current = true
    connect()
    return () => {
      isMounted.current = false
      clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null  // Prevent reconnect on intentional close
        wsRef.current.close()
      }
    }
  }, [connect])

  return { data, status, reconnect: connect }
}
