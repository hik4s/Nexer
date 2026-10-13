import { useEffect, useState } from "react";

import { executionEventsUrl, type ExecutionEvent } from "../lib/api";

export function useExecutionEvents(executionId: number | null) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    setEvents([]);
    setConnected(false);
    if (executionId == null) return;

    let lastId = 0;

    const source = new EventSource(executionEventsUrl(executionId), { withCredentials: true });

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);

    const eventTypes = [
      "worker.execution.claimed",
      "automation.started",
      "action.started",
      "action.finished",
      "checkpoint",
      "step.started",
      "step.finished",
      "step.failed",
      "automation.finished",
      "automation.failed",
      "automation.cancelled",
      "execution.cancel_requested",
      "execution.cancelled",
      "execution.finished",
      "browser.close_failed",
    ];

    const handlers = eventTypes.map((type) => {
      const handler = (event: MessageEvent<string>) => {
        const id = Number(event.lastEventId);
        if (!Number.isSafeInteger(id) || id <= lastId) return;
        let payload: Record<string, unknown>;
        try {payload = JSON.parse(event.data || "{}");} catch {return;}
        lastId = id;
        setEvents((current) => [
          ...current.slice(-499),
          {
            id,
            type,
            level: type.endsWith("failed") ? "ERROR" : "INFO",
            message: type.replaceAll(".", " "),
            payload,
            created_at: new Date().toISOString(),
          },
        ]);
      };

      source.addEventListener(type, handler);
      return { type, handler };
    });

    return () => {
      handlers.forEach(({ type, handler }) =>
        source.removeEventListener(type, handler),
      );
      source.close();
    };
  }, [executionId]);

  return { events, connected };
}
