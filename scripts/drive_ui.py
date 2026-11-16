import os, sys, time, traceback
from playwright.sync_api import sync_playwright

BASE = 'https://localhost:8834'
U = os.environ['NESSUS_USER']
P = os.environ['NESSUS_PASS']
NAME = 'Exp15 Basic Network Scan'
os.makedirs('shots', exist_ok=True)
count = [0]

def shot(page, name):
    count[0] += 1
    page.screenshot(path='shots/%02d_%s.png' % (count[0], name))
    print('shot', name, flush=True)

def run(page):
    page.goto(BASE + '/#/')
    page.wait_for_timeout(6000)
    shot(page, 'login_page')
    page.locator('input[type=password]').first.fill(P)
    page.locator('input:not([type=password]):not([type=hidden]):not([type=checkbox])').first.fill(U)
    page.keyboard.press('Enter')
    page.wait_for_timeout(10000)
    shot(page, 'after_login')
    page.goto(BASE + '/#/scans/reports/new')
    page.wait_for_timeout(5000)
    shot(page, 'scan_templates')
    page.get_by_text('Basic Network Scan').first.click()
    page.wait_for_timeout(4000)
    page.locator('input[type=text]:visible').first.fill(NAME)
    page.locator('textarea:visible').last.fill('127.0.0.1')
    shot(page, 'basic_scan_settings')
    page.get_by_role('button', name='Save').first.click()
    page.wait_for_timeout(5000)
    shot(page, 'scan_saved')
    page.get_by_text(NAME).first.click()
    page.wait_for_timeout(4000)
    page.get_by_role('button', name='Launch').first.click()
    page.wait_for_timeout(30000)
    shot(page, 'scan_running')
    for i in range(90):
        page.wait_for_timeout(20000)
        page.reload()
        page.wait_for_timeout(4000)
        txt = page.inner_text('body')
        print(i, 'Completed' in txt, flush=True)
        if 'Completed' in txt:
            break
    shot(page, 'scan_completed_hosts')
    page.get_by_text('Vulnerabilities').first.click()
    page.wait_for_timeout(4000)
    shot(page, 'vulnerabilities_tab')
    rows = page.locator('table tbody tr')
    if rows.count() > 0:
        rows.first.click()
        page.wait_for_timeout(4000)
        shot(page, 'vulnerability_detail')

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=['--ignore-certificate-errors', '--no-sandbox', '--window-size=1366,768'])
    ctx = b.new_context(ignore_https_errors=True, viewport={'width': 1366, 'height': 768})
    page = ctx.new_page()
    try:
        run(page)
    except Exception:
        traceback.print_exc()
        shot(page, 'ERROR')
        open('shots/debug.html', 'w').write(page.content())
        sys.exit(1)
    os.system('import -window root shots/99_xvfb_final_desktop.png')
