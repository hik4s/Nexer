"""Offline recorder prototype: fresh Edge, loopback fixture, parameterized draft."""
import argparse
import json
from pathlib import Path
import sys
from threading import Event
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
for relative in ("apps/runtime", "apps/recorder"):
    sys.path.insert(0, str(ROOT / relative))
from nexer_recorder.compiler import Recording
from playwright.sync_api import sync_playwright


def main(*, stop_event=None, finish_event=None):
    finish_event = finish_event or Event()
    parser = argparse.ArgumentParser(description="Gravar locais de ações sem capturar valores preenchidos.")
    parser.add_argument("--url", required=True, help="Página de teste local HTTP loopback.")
    parser.add_argument("--output", required=True, type=Path, help="Arquivo JSON novo para revisão no Studio.")
    parser.add_argument("--name", default="Receita gravada")
    parser.add_argument("--download-selector", action="append", default=[], help="Seletor de botão que inicia download; pode repetir.")
    options = parser.parse_args()
    url = urlsplit(options.url)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment:
        parser.error("Esta versão aceita somente páginas de teste locais, sem dados na URL.")
    if options.output.exists():
        parser.error("Escolha um arquivo novo; receitas existentes são preservadas.")
    recording = Recording(options.name)
    origin = (url.scheme, url.hostname, url.port)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False, args=["--disable-features=msDownloadsHub"])
        context = browser.new_context(accept_downloads=False, service_workers="block")
        def route(request_route):
            target = urlsplit(request_route.request.url)
            if (target.scheme, target.hostname, target.port) == origin:
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
        known_pages = []
        def reject_context(*_):
            if not unsupported:
                print("Ação não suportada ou inválida. O rascunho não será salvo; revise o componente da página.")
            unsupported.append(True)
        def capture(source, event):
            nonlocal active_page
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
                recording.accept(event)
                if event.get("action") == "download":
                    expected_downloads[source_page] = expected_downloads.get(source_page, 0) + 1
            except Exception:
                reject_context()
        context.expose_binding("nexerCapture", capture)
        context.expose_binding("nexerUnsupported", reject_context)
        context.expose_binding("nexerFinishRecording", lambda source: finish_event.set())
        context.add_init_script(path=ROOT / "apps/recorder/nexer_recorder/capture.js")
        context.add_init_script("window.__nexerDownloadSelectors = " + json.dumps(options.download_selector))
        page = context.new_page()
        def attach_downloads(source_page):
            known_pages.append(source_page)
            def closed(_):
                nonlocal active_page
                if finishing or source_page is page:
                    return
                index = known_pages.index(source_page)
                known_pages.remove(source_page)
                if source_page is not active_page:
                    recording.accept({"action": "switch_tab", "index": index})
                recording.accept({"action": "close_tab"})
                active_page = None
            def download(_):
                observed_downloads[source_page] = observed_downloads.get(source_page, 0) + 1
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
        except KeyboardInterrupt:
            pass
        except Exception:
            if not page.is_closed():
                raise RuntimeError("RECORDER_BROWSER_FAILED") from None
        finally:
            finishing = True
            context.close()
            browser.close()
    if unsupported:
        raise RuntimeError("RECORDER_CONTEXT_UNSUPPORTED")
    if stop_event is not None and stop_event.is_set(): raise RuntimeError("RECORDER_CANCELLED")
    if observed_downloads != expected_downloads:
        raise RuntimeError("RECORDER_DOWNLOAD_UNSUPPORTED")
    with options.output.open("x", encoding="utf-8") as target:
        json.dump(recording.recipe(), target, ensure_ascii=False, indent=2)
    print("Rascunho salvo. Revise seletores e nomes dos inputs no Studio antes de validar.")


if __name__ == "__main__":
    main()
