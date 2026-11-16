import os, sys, time, traceback, ssl, urllib.request
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

def status():
    ctx = ssl._create_unverified_context()
    try:
        return urllib.request.urlopen(BASE + '/server/status', context=ctx, timeout=10).read().decode()
    except Exception as e:
        return 'ERR %s' % e

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
    for step in range(25):
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
        elif 'Skip' in t:
            page.get_by_text('Skip').first.click()
        elif page.locator('input[type=password]:visible').count() > 0:
            page.locator('input[type=text]:visible, input:not([type]):visible').first.fill(U)
            pw = page.locator('input[type=password]:visible')
            for k in range(pw.count()):
                pw.nth(k).fill(P)
            shot(page, 'create_admin_account')
            page.get_by_role('button', name='Submit').first.click()
            break
        elif page.locator('input:visible').count() > 0 and not code_done:
            page.locator('input:visible').first.fill(CODE)
            cont(page)
            code_done = True
        page.wait_for_timeout(10000)
    page.wait_for_timeout(8000)
    shot(page, 'initializing_plugins')
    for i in range(240):
        s = status()
        print(i, s, flush=True)
        if 'ready' in s:
            break
        time.sleep(15)
    page.goto(BASE + '/')
    page.wait_for_timeout(8000)
    shot(page, 'nessus_ready')

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
