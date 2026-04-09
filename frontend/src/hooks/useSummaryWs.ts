import { useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"

/**
 * Opens a one-shot WebSocket while `isProcessing` is true.
 * When the server notifies that the summary left "processing",
 * the patient query cache is invalidated (triggers a single refetch).
 *
 * Falls back to reconnect with backoff if the connection drops
 * before a notification arrives.
 */
export function useSummaryWs(patientId: string, isProcessing: boolean) {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!isProcessing) return

    const token = localStorage.getItem("access_token")
    if (!token) return

    let disposed = false
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let ws: WebSocket | null = null
    let attempt = 0

    function connect() {
      if (disposed) return

      const base = import.meta.env.VITE_API_URL as string
      const wsBase = base.replace(/^http/, "ws")
      const url = `${wsBase}/api/v1/ws/patients/${patientId}/summary?token=${encodeURIComponent(token!)}`

      ws = new WebSocket(url)
      let receivedNotification = false

      ws.onmessage = (event) => {
        receivedNotification = true
        const data = JSON.parse(event.data) as { status: string }
        if (data.status && data.status !== "processing") {
          disposed = true
          queryClient.invalidateQueries({ queryKey: ["patients", patientId] })
        }
      }

      ws.onclose = () => {
        ws = null
        if (disposed || receivedNotification) return
        // Reconnect with exponential backoff (max ~16 s)
        const delay = Math.min(1000 * 2 ** attempt, 16_000)
        attempt++
        retryTimer = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        /* onclose always fires after onerror — reconnect handled there */
      }
    }

    connect()

    return () => {
      disposed = true
      if (retryTimer) clearTimeout(retryTimer)
      if (ws) ws.close()
    }
  }, [patientId, isProcessing, queryClient])
}
