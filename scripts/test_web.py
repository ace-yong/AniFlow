import sys, os, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ.pop('QT_QPA_PLATFORM', None)
import webview
from gui import Api, VERSION

api = Api()
html = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'index.html')
print('HTML exists:', os.path.isfile(html))

result = {'window': None}
def create():
    result['window'] = webview.create_window('AniFlow Debug', html, js_api=api, width=1100, height=700)

t = threading.Thread(target=create, daemon=True)
t.start()
time.sleep(3)
print('Windows:', len(webview.windows))
if webview.windows:
    print('Window title:', webview.windows[0].title)
    webview.windows[0].destroy()
    print('Closed')
else:
    print('FAIL: No window created')
