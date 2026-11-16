import os, sys, time, traceback
from playwright.sync_api import sync_playwright

BASE = 'https://localhost:8834'
U = os.environ['NESSUS_USER']
P = os.environ['NESSUS_PASS']
CODE = os.environ['NESSUS_CODE']
MASK = 'XXXX-XXXX-XXXX-XXXX-XXXX'
os.makedirs('shots', exist_ok=True)
count = [0]

JS = '''c => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n; while (n = w.nextNode()) { n.nodeValue = n.nodeValue.split(c).join('XXXX-XXXX-XXXX-XXXX-XXXX'); } document.querySelectorAll('input').forEach(i => { if (i.type !== 'password' && i.value && i.value.indexOf(c) >= 0) { i.value = 'XXXX-XXXX-XXXX-XXXX-XXXX'; } }); }'''

def shot(page, name):
    count[0] += 1
    try:
        page.evaluate(JS, CODE)
    except Exception as e:
        print('mask failed', e, flush=True)
    page.screenshot(path='shots/w%02d_%s.png' % (count[0], name))
    print('shot', name, flush=True)

def body(page):
    return page.inner_text('body')

def cont(page):
    page.get_by_role('button', name='Continue').first.click()

def run(page):
    page.goto(BASE + '/')
    for i in range(90):
        page.wait_for_timeout(8000)
        t = body(page)
        print('wait', i, repr(t[:60]), flush=True)
        if 'Welcome to Nessus' in t:
            break
        if i % 4 == 3:
            page.reload()
    code_done = False
    submitted = False
    for step in range(30):
        t = body(page)
        print('step', step, repr(t[:100].replace(CODE, MASK)), flush=True)
        shot(page, 'step%02d' % step)
        if 'Register for Nessus Essentials' in t:
            page.get_by_text('Register for Nessus Essentials').first.click()
            page.wait_for_timeout(800)
            cont(page)
        elif 'Register Offline' in t:
            cont(page)
        elif 'License Information' in t:
            cont(page)
        elif 'Get an activation code' in t:
            page.get_by_role('button', name='Skip', exact=True).click()
        elif page.locator('input[type=password]:visible').count() > 0:
            page.locator('input[type=text]:visible, input:not([type]):visible').first.fill(U)
            pw = page.locator('input[type=password]:visible')
            for k in range(pw.count()):
                pw.nth(k).fill(P)
            shot(page, 'create_admin_account')
            page.get_by_role('button', name='Submit').first.click()
            submitted = True
            break
        elif page.locator('input:visible').count() > 0 and not code_done:
            page.locator('input:visible').first.fill(CODE)
            cont(page)
            code_done = True
        page.wait_for_timeout(10000)
    if not submitted:
        raise RuntimeError('wizard did not reach account creation')
    page.wait_for_timeout(10000)
    shot(page, 'initializing_plugins')
    for i in range(240):
        page.goto(BASE + '/')
        page.wait_for_timeout(8000)
        t = body(page)
        print('plugins', i, repr(t[:80]), flush=True)
        if 'Sign In' in t or 'Sign in' in t:
            break
        time.sleep(12)
    shot(page, 'nessus_ready_login')

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=['--ignore-certificate-errors', '--no-sandbox', '--window-size=1366,768'])
    ctx = b.new_context(ignore_https_errors=True, viewport={'width': 1366, 'height': 768})
    page = ctx.new_page()
    try:
        run(page)
    except Exception:
        traceback.print_exc()
        shot(page, 'ERROR')
        open('shots/wizard_debug.html', 'w').write(page.content().replace(CODE, MASK))
        sys.exit(1)
