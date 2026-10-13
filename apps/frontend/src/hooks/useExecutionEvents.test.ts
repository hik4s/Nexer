import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useExecutionEvents } from "./useExecutionEvents";

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, (event: MessageEvent) => void>();
  closed = false;

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, listener);
  }

  close() {
    this.closed = true;
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    if (this.listeners.get(type) === listener) {
      this.listeners.delete(type);
    }
  }

  emitOpen() {
    this.onopen?.();
  }

  emit(type: string, data: unknown, lastEventId = "1") {
    const listener = this.listeners.get(type);
    listener?.(
      new MessageEvent(type, {
        data: JSON.stringify(data),
        lastEventId,
      }),
    );
  }
}

describe("useExecutionEvents", () => {
  it("deduplicates replayed events and clears the previous execution", () => {
    const {result, rerender} = renderHook(({id}) => useExecutionEvents(id), {initialProps: {id: 7 as number | null}});
    act(() => {FakeEventSource.instances[0].emit("action.finished", {}, "12"); FakeEventSource.instances[0].emit("action.finished", {}, "12");});
    expect(result.current.events).toHaveLength(1);
    rerender({id: null});
    expect(result.current.events).toHaveLength(0);
    expect(FakeEventSource.instances[0].closed).toBe(true);
  });
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("connects and stores typed execution events", () => {
    const { result } = renderHook(() => useExecutionEvents(7));

    expect(result.current.connected).toBe(false);
    expect(FakeEventSource.instances[0].url).toContain("/executions/7/events");

    act(() => {
      FakeEventSource.instances[0].emitOpen();
      FakeEventSource.instances[0].emit(
        "automation.finished",
        { status: "SUCCEEDED" },
        "12",
      );
    });

    expect(result.current.connected).toBe(true);
    expect(result.current.events[0]).toEqual(
      expect.objectContaining({
        id: 12,
        type: "automation.finished",
        payload: { status: "SUCCEEDED" },
      }),
    );
  });

  it("closes the stream on unmount", () => {
    const { unmount } = renderHook(() => useExecutionEvents(9));

    const source = FakeEventSource.instances[0];
    unmount();

    expect(source.closed).toBe(true);
  });
});
