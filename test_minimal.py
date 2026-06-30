import sys, os, webview
VERSION = "1.1.0"
def start():
    webview.create_window("AniFlow Test", html="<h1>Hello</h1><p>If you see this, WebView2 works!</p>", width=400, height=300)
if __name__ == "__main__":
    start()
