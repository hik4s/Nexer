"""Fresh Edge recorder with manual HTTPS preparation and parameterized drafts."""
import argparse
import json
from pathlib import Path
import sys
from time import monotonic
from threading import Event
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
for relative in ("apps/runtime", "apps/recorder"):
    sys.path.insert(0, str(ROOT / relative))
from site_urls import validate_site_url, site_origin
from nexer_recorder.compiler import Recording
from playwright.sync_api import sync_playwright


def main(*, stop_event=None, finish_event=None, on_started=None):
    finish_event = finish_event or Event()
    parser = argparse.ArgumentParser(description="Gravar locais de ações sem capturar valores preenchidos.")
    parser.add_argument("--url", required=True, help="Página HTTPS ou HTTP loopback; rota segura após # permitida.")
    parser.add_argument("--output", required=True, type=Path, help="Arquivo JSON novo para revisão no Studio.")
    parser.add_argument("--name", default="Receita gravada")
    parser.add_argument("--download-selector", action="append", default=[], help="Seletor de botão que inicia download; pode repetir.")
    parser.add_argument("--smart-waits", action="store_true", help="Adicionar esperas inteligentes revisaveis.")
    options = parser.parse_args()
    try:
        options.url = validate_site_url(options.url)
    except ValueError:
        parser.error("Informe HTTPS ou HTTP local, sem credenciais ou parâmetros; use somente uma rota segura no fragmento.")
    preparing = urlsplit(options.url).scheme == "https"
    if options.output.exists():
        parser.error("Escolha um arquivo novo; receitas existentes são preservadas.")
    recording = Recording(options.name)
    origin = site_origin(options.url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False, args=["--disable-features=msDownloadsHub"])
        context = browser.new_context(accept_downloads=False, service_workers="block")
        def route(request_route):
            try:
                permitted = site_origin(request_route.request.url) == origin
            except ValueError:
                permitted = False
            if permitted:
                response = request_route.fetch(max_redirects=0)
                if 300 <= response.status < 400:
                    request_route.abort()
                else:
                    request_route.fulfill(response=response)
            else:
                request_route.abort()
        context.route("**/*", route)
        # Intercept without connect_to_server; sync close inside this callback
        # can deadlock the installed Playwright dispatcher.
        context.route_web_socket("**/*", lambda socket: None)
        unsupported = []
        active_page = None
        finishing = False
        expected_downloads = {}
        observed_downloads = {}
        observed_download_at = {}
        known_pages = []
        recent_click = None

        def reconcile_download(source_page):
            nonlocal recent_click
            if observed_downloads.get(source_page, 0) <= expected_downloads.get(source_page, 0):
                return
            if recent_click is None:
                return
            candidate_page, step_index, when = recent_click
            observed_at = observed_download_at.get(source_page, 0)
            # A browser callback can very slightly precede the Playwright binding.
            if candidate_page is not source_page or not -0.15 <= observed_at - when <= 2.5:
                return
            try:
                recording.promote_recent_click_to_download(step_index=step_index)
            except ValueError:
                return
            expected_downloads[source_page] = expected_downloads.get(source_page, 0) + 1
            recent_click = None

        def reject_context(*_):
            if preparing: return
            if not unsupported:
                print("Ação não suportada ou inválida. O rascunho não será salvo; revise o componente da página.")
            unsupported.append(True)
        def capture(source, event):
            nonlocal active_page, recent_click
            if preparing: return
            try:
                source_page = source["page"]
                if event.get("action") in {"scroll", "hover"} and active_page is not None and source_page is not active_page:
                    return
                if source_page is not active_page:
                    index = context.pages.index(source_page)
                    if len(recording.steps) > 1 or index != 0:
                        recording.accept({"action": "switch_tab", "index": index})
                    active_page = source_page
                if source["frame"].parent_frame is not None and not event.get("frames"):
                    raise ValueError("RECORDER_FRAME_UNSUPPORTED")
                readiness = event.get("readiness")
                if readiness is not None:
                    if readiness != "enabled" or event.get("action") not in {"click", "download"}:
                        raise ValueError("RECORDER_EVENT_INVALID")
                    event = {key: value for key, value in event.items() if key != "readiness"}
                    if not (event.get("action") == "download" and "collection" in event):
                        previous = recording.steps[-1]
                        if not (previous.get("action") == "wait_for"
                                and previous.get("selector") == event.get("selector")
                                and previous.get("frames", []) == event.get("frames", [])):
                            recording.accept({"action": "wait_for", "selector": event["selector"],
                                              "frames": event.get("frames", []), "state": "enabled",
                                              "learning": {"source": "automatic", "confidence": "high"}})
                recording.accept(event)
                if event.get("action") == "click" and event.get("button", "left") == "left" and event.get("click_count", 1) == 1:
                    recent_click = (source_page, len(recording.steps) - 1, monotonic())
                    reconcile_download(source_page)
                else:
                    recent_click = None
                if event.get("action") == "download":
                    expected_downloads[source_page] = expected_downloads.get(source_page, 0) + 1
            except Exception:
                reject_context()
        start_requests = []
        start_result = {"pending": False, "started": not preparing}
        def request_start(source):
            if not start_requests:
                start_requests.append(source)
                start_result.clear()
                start_result.update(pending=True, started=False)
            return dict(start_result)
        def start_recording(source):
            nonlocal preparing, active_page
            if not preparing: return {"started": True}
            source_page = source["page"]
            try:
                matches = validate_site_url(source_page.url) == options.url
            except ValueError:
                matches = False
            if source["frame"].parent_frame is not None or source_page is not page or not matches:
                return {"started": False, "message": "Abra a página e a rota configuradas antes de iniciar."}
            if len(context.pages) != 1:
                return {"started": False, "message": "Feche as abas abertas durante a preparação e volte à página original."}
            password_visible = False
            for frame in source_page.frames:
                if frame.parent_frame is not None:
                    owner = frame.frame_element()
                    try:
                        if not owner.is_visible(): continue
                    finally:
                        owner.dispose()
                if frame.locator('input[type="password"]:visible').count():
                    password_visible = True
                    break
            if password_visible:
                return {"started": False, "message": "Conclua o login manual antes de iniciar."}
            known_pages[:] = [page]
            preparing = False
            active_page = source_page
            expected_downloads.clear()
            observed_downloads.clear()
            observed_download_at.clear()
            for current in context.pages:
                for frame in current.frames:
                    try: frame.evaluate("window.__nexerRecorderActive = true")
                    except Exception: pass
            if on_started is not None: on_started()
            return {"started": True}
        context.expose_binding("nexerStartRecording", request_start)
        context.expose_binding("nexerStartRecordingStatus", lambda source: dict(start_result))
        context.expose_binding("nexerRecordingState", lambda source: not preparing)
        context.add_init_script("for (const name of ['Worker', 'SharedWorker']) window[name] = class { constructor() { throw new Error('RECORDER_WORKER_UNSUPPORTED'); } };")
        context.expose_binding("nexerCapture", capture)
        context.expose_binding("nexerUnsupported", reject_context)
        context.expose_binding("nexerFinishRecording", lambda source: finish_event.set() if not preparing else None)
        context.add_init_script(path=ROOT / "apps/recorder/nexer_recorder/capture.js")
        context.add_init_script("window.__nexerDownloadSelectors = " + json.dumps(options.download_selector))
        page = context.new_page()
        def attach_downloads(source_page):
            known_pages.append(source_page)
            def closed(_):
                nonlocal active_page
                if source_page not in known_pages: return
                index = known_pages.index(source_page)
                known_pages.remove(source_page)
                if finishing or preparing or source_page is page:
                    return
                if source_page is not active_page:
                    recording.accept({"action": "switch_tab", "index": index})
                recording.accept({"action": "close_tab"})
                active_page = None
            def download(_):
                if preparing: return
                observed_downloads[source_page] = observed_downloads.get(source_page, 0) + 1
                observed_download_at[source_page] = monotonic()
                reconcile_download(source_page)
            source_page.on("download", download)
            source_page.on("close", closed)
        context.on("page", attach_downloads)
        attach_downloads(page)
        try:
            page.goto(options.url)
            print("Gravando locais de ações. Use Parar gravação na página para revisar os campos.")
            while not page.is_closed():
                if stop_event is not None and stop_event.is_set(): break
                if finish_event is not None and finish_event.is_set(): break
                page.wait_for_timeout(250)
                if start_requests:
                    source = start_requests.pop(0)
                    try:
                        result = start_recording(source)
                    except Exception:
                        result = {"started": False, "message": "Não foi possível iniciar. Revise a página configurada."}
                    start_result.clear()
                    start_result.update(result)
        except KeyboardInterrupt:
            pass
        except Exception:
            if not page.is_closed():
                raise RuntimeError("RECORDER_BROWSER_FAILED") from None
        finally:
            finishing = True
            context.close()
            browser.close()
    if stop_event is not None and stop_event.is_set(): raise RuntimeError("RECORDER_CANCELLED")
    if preparing or len(recording.steps) <= 1:
        raise RuntimeError("RECORDER_EMPTY")
    if unsupported:
        raise RuntimeError("RECORDER_CONTEXT_UNSUPPORTED")
    if observed_downloads != expected_downloads:
        raise RuntimeError("RECORDER_DOWNLOAD_UNSUPPORTED")
    with options.output.open("x", encoding="utf-8") as target:
        recipe = recording.recipe()
        if options.smart_waits:
            from nexer_recorder.smart_waits import optimize_recipe
            recipe = optimize_recipe(recipe)
        json.dump(recipe, target, ensure_ascii=False, indent=2)
    print("Rascunho salvo. Revise seletores e nomes dos inputs no Studio antes de validar.")


if __name__ == "__main__":
    main()
