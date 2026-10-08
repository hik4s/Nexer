import time
from threading import Event


class WorkerLoop:
    def __init__(
        self,
        *,
        service,
        processor,
        heartbeat_every_ticks: int = 10,
        poll_interval: float = 1.0,
    ):
        if heartbeat_every_ticks < 1:
            raise ValueError("heartbeat_every_ticks must be >= 1")
        if poll_interval < 0:
            raise ValueError("poll_interval must be >= 0")

        self.service = service
        self.processor = processor
        self.heartbeat_every_ticks = heartbeat_every_ticks
        self.poll_interval = poll_interval
        self._ticks = 0

    def tick(self):
        self._ticks += 1
        if self._ticks % self.heartbeat_every_ticks == 0:
            self.service.heartbeat()
        return self.processor.process_once()

    def run(self, *, stop_event: Event, sleep=time.sleep):
        self.service.register()
        self.service.recover_stale_executions()
        self._ticks = 0

        try:
            while not stop_event.is_set():
                self.tick()
                if self.poll_interval:
                    sleep(self.poll_interval)
        finally:
            self.service.stop()
