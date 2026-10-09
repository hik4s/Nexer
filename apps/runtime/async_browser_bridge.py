"""Synchronous facade over public async Playwright APIs on an owned loop thread."""
import asyncio
import inspect
from threading import Event, Thread


class BrowserThread:
    def __init__(self):
        self._ready = Event()
        self._loop = None
        self._thread = Thread(target=self._serve, name="nexer-corporate-browser", daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            raise RuntimeError("CORPORATE_CONTEXT_UNAVAILABLE")

    def _serve(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            tasks = asyncio.all_tasks(self._loop)
            for task in tasks:
                task.cancel()
            if tasks:
                self._loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.run_until_complete(self._loop.shutdown_default_executor())
            self._loop.close()

    def run(self, coroutine):
        if not self._thread.is_alive() or self._loop.is_closed():
            coroutine.close()
            raise RuntimeError("CORPORATE_BROWSER_OPERATION_FAILED")
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=70)
        except Exception:
            future.cancel()
            raise RuntimeError("CORPORATE_BROWSER_OPERATION_FAILED") from None

    def wrap(self, value):
        if value is None or isinstance(value, (str, bytes, bool, int, float)):
            return value
        if isinstance(value, list):
            return [self.wrap(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.wrap(item) for item in value)
        if isinstance(value, dict):
            return {key: self.wrap(item) for key, item in value.items()}
        return BrowserProxy(self, value)


    def unwrap(self, value):
        if isinstance(value, BrowserProxy):
            if value._bridge is not self:
                raise RuntimeError("CORPORATE_BROWSER_OPERATION_FAILED")
            return value._target
        if isinstance(value, list):
            return [self.unwrap(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.unwrap(item) for item in value)
        if isinstance(value, dict):
            return {key: self.unwrap(item) for key, item in value.items()}
        return value

    def stop(self):
        if self._thread.is_alive():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=10)
        if self.is_alive():
            raise RuntimeError("CORPORATE_BROWSER_SHUTDOWN_FAILED")

    def is_alive(self):
        return self._thread.is_alive()


class BrowserProxy:
    def __init__(self, bridge, target):
        self._bridge = bridge
        self._target = target

    async def _lookup(self, name):
        try:
            value = getattr(self._target, name)
        except AttributeError:
            return "missing", None
        if callable(value):
            return "method", None
        if inspect.isawaitable(value):
            value = await value
        return "value", value

    async def _call(self, name, args, kwargs):
        if name in {"route", "route_web_socket", "on"}:
            callback = args[-1]
            async def adapter(*event_args):
                wrapped = [self._bridge.wrap(value) for value in event_args]
                await asyncio.to_thread(callback, *wrapped)
            args = (*args[:-1], adapter)
        args = self._bridge.unwrap(args)
        kwargs = self._bridge.unwrap(kwargs)
        result = getattr(self._target, name)(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    def __getattr__(self, name):
        kind, value = self._bridge.run(self._lookup(name))
        if kind == "missing":
            raise AttributeError(name)
        if kind == "method":
            def invoke(*args, **kwargs):
                return self._bridge.wrap(self._bridge.run(self._call(name, args, kwargs)))
            return invoke
        return self._bridge.wrap(value)

    def __enter__(self):
        return self._bridge.wrap(self._bridge.run(self._call("__aenter__", (), {})))

    def __exit__(self, *args):
        return self._bridge.run(self._call("__aexit__", args, {}))

    def __repr__(self):
        return "CorporateBrowserProxy()"
