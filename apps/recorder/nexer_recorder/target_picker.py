"""Fresh, owner-controlled target acquisition; no recipe replay or field values."""
from pathlib import Path
from time import monotonic
from playwright.sync_api import sync_playwright
from target_picker_contract import validate_configuration, validate_target
from site_urls import site_origin


def target_script() -> str:
    root = Path(__file__).resolve().parent
    return '\n'.join((root / name).read_text(encoding='utf-8-sig') for name in ('selectors.js', 'target_capture.js'))


def validate_selection(source, event, page, kind):
    target = validate_target(event)
    if source.get('page') is not page or source.get('frame') is not page.main_frame:
        raise ValueError('TARGET_PICKER_CONTEXT_UNSUPPORTED')
    locator = page.locator('css=' + target['selector'])
    if locator.count() != 1 or not locator.is_visible():
        raise ValueError('TARGET_PICKER_FAILED')
    compatible = locator.evaluate('''(n,kind)=>{
        if(window.__nexerTargetPicker?.selected!==n || !n.isConnected) return false;
        if(n.matches('html,body,canvas,iframe,input[type="password"],input[type="hidden"],input[type="file"]')) return false;
        const rules={text:'input:not([type]),input[type="text"],input[type="search"],input[type="email"],input[type="url"],input[type="tel"],input[type="number"],input[type="date"],input[type="datetime-local"],input[type="time"],input[type="month"],input[type="week"],textarea,[contenteditable="true"],[contenteditable=""]',
          select:'select',checkbox:'input[type="checkbox"]',range:'input[type="range"]',color:'input[type="color"]'};
        return kind==='element' || (rules[kind] && n.matches(rules[kind]));
    }''', kind, timeout=250)
    if not compatible:
        raise ValueError('TARGET_PICKER_FAILED')
    return target


def pick_target(configuration, stop_event, on_phase, *, headless=False, timeout=300):
    cfg = validate_configuration(configuration)
    origin = site_origin(cfg['url'])
    deadline = monotonic() + timeout
    if stop_event.is_set():
        raise RuntimeError('TARGET_PICKER_CANCELLED')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=headless, args=['--disable-features=msDownloadsHub'])
        try:
            context = browser.new_context(accept_downloads=False, service_workers='block')
            phase, page, document = 'PREPARING', None, None
            commands, candidates = [], []

            def route(request_route):
                try:
                    permitted = site_origin(request_route.request.url) == origin
                    permitted = permitted and (phase != 'SELECTING' or request_route.request.method in {'GET', 'HEAD'})
                    if not permitted:
                        request_route.abort(); return
                    response = request_route.fetch(max_redirects=0, timeout=10000)
                    if 300 <= response.status < 400: request_route.abort()
                    else: request_route.fulfill(response=response)
                except Exception:
                    try: request_route.abort()
                    except Exception: pass

            def enqueue_command(source, command):
                if (source['page'] is page and source['frame'] is page.main_frame
                        and isinstance(command, str) and command in {'activate', 'prepare', 'cancel'} and not commands):
                    commands.append(command)

            def enqueue_candidate(source, event):
                if phase == 'SELECTING' and not candidates:
                    candidates.append((source, event))

            context.route('**/*', route)
            context.route_web_socket('**/*', lambda socket: None)
            context.add_init_script("for(const name of ['Worker','SharedWorker']) window[name]=class {constructor(){throw new Error('TARGET_PICKER_CONTEXT_UNSUPPORTED')}};")
            context.expose_binding('nexerTargetState', lambda source: {'active': phase == 'SELECTING', 'kind': cfg['kind']})
            context.expose_binding('nexerTargetCommand', enqueue_command)
            context.expose_binding('nexerTargetCandidate', enqueue_candidate)
            context.add_init_script(target_script())
            page = context.new_page()

            def set_active(value, message=''):
                for frame in page.frames:
                    try:
                        frame.evaluate('(args)=>window.__nexerTargetPicker?.setActive(...args)', [value, cfg['kind'], message])
                    except Exception:
                        pass

            page.goto(cfg['url'], wait_until='domcontentloaded', timeout=15000)
            while not page.is_closed() and not stop_event.is_set() and monotonic() < deadline:
                page.wait_for_timeout(100)
                if document is not None:
                    try:
                        same = page.locator(':root').evaluate('(root,pin)=>root===pin', document, timeout=250)
                    except Exception:
                        same = False
                    if not same:
                        raise RuntimeError('TARGET_PICKER_CONTEXT_UNSUPPORTED')
                if commands:
                    command = commands.pop(0)
                    if command == 'cancel':
                        raise RuntimeError('TARGET_PICKER_CANCELLED')
                    if command == 'prepare':
                        phase = 'PREPARING'; candidates.clear()
                        if document is not None: document.dispose(); document = None
                        set_active(False); on_phase(phase)
                    elif command == 'activate':
                        valid = len(context.pages) == 1 and site_origin(page.url) == origin
                        valid = valid and not any(frame.locator('input[type="password"]:visible').count() for frame in page.frames)
                        if not valid:
                            set_active(False, 'Conclua o login, feche outras abas e volte à página da etapa na origem configurada.'); continue
                        if document is not None: document.dispose()
                        document = page.locator(':root').element_handle(timeout=250)
                        phase = 'SELECTING'; candidates.clear(); set_active(True); on_phase(phase)
                if candidates:
                    source, event = candidates.pop(0)
                    try:
                        target = validate_selection(source, event, page, cfg['kind'])
                    except Exception:
                        set_active(True, 'Escolha um alvo compatível na página principal. Frames e controles especiais usam correção manual.'); continue
                    if stop_event.is_set():
                        raise RuntimeError('TARGET_PICKER_CANCELLED')
                    return target
            raise RuntimeError('TARGET_PICKER_CANCELLED' if stop_event.is_set() or page.is_closed() else 'TARGET_PICKER_TIMEOUT')
        finally:
            browser.close()
