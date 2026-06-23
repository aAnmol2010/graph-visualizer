import json
import traceback
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture console messages
        def on_console(msg):
            print(f"CONSOLE: {msg.type}: {msg.text}")
            if msg.type == 'error':
                print(msg.location)
                
        page.on("console", on_console)
        
        # Capture errors
        def on_page_error(err):
            print(f"PAGE ERROR: {err.message}")
            print(f"STACK: {err.stack}")
            
        page.on("pageerror", on_page_error)
        
        try:
            print("Navigating to http://127.0.0.1:5000")
            page.goto("http://127.0.0.1:5000")
            page.evaluate("sessionStorage.clear()")
            page.reload()
            page.fill("#add-node-id", "1")
            page.click("button:has-text('Add node')")
            page.fill("#bfs-start", "1")
            page.click("button:has-text('Run BFS')")
            page.wait_for_load_state("networkidle")
            
        except Exception as e:
            pass
            
        browser.close()

run()
