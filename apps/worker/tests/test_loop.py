import unittest


from loop import WorkerLoop


class FakeStopEvent:
    def __init__(self, stop_after_checks=2):
        self.checks = 0
        self.stop_after_checks = stop_after_checks

    def is_set(self):
        self.checks += 1
        return self.checks >= self.stop_after_checks


class FakeService:
    def __init__(self):
        self.register_calls = 0
        self.heartbeat_calls = 0

    def register(self):
        self.register_calls += 1

    def heartbeat(self):
        self.heartbeat_calls += 1


class FakeProcessor:
    def __init__(self):
        self.calls = 0

    def process_once(self):
        self.calls += 1
        return {"status": "IDLE"}


class WorkerLoopTests(unittest.TestCase):
    def test_tick_heartbeats_and_processes_once(self):
        service = FakeService()
        processor = FakeProcessor()
        loop = WorkerLoop(
            service=service,
            processor=processor,
            heartbeat_every_ticks=1,
        )

        result = loop.tick()

        self.assertEqual(result["status"], "IDLE")
        self.assertEqual(service.heartbeat_calls, 1)
        self.assertEqual(processor.calls, 1)

    def test_run_registers_and_stops_cleanly(self):
        service = FakeService()
        processor = FakeProcessor()
        loop = WorkerLoop(
            service=service,
            processor=processor,
            heartbeat_every_ticks=1,
        )
        stop_event = FakeStopEvent(stop_after_checks=2)

        loop.run(stop_event=stop_event, sleep=lambda _: None)

        self.assertEqual(service.register_calls, 1)
        self.assertGreaterEqual(service.heartbeat_calls, 1)
        self.assertGreaterEqual(processor.calls, 1)


if __name__ == "__main__":
    unittest.main()
