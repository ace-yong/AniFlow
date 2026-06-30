import urllib.request, json

req = urllib.request.Request('https://api.github.com/repos/MaaXYZ/MaaEnd/releases/latest', headers={'User-Agent': 'AniFlow/1.0'})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
print('Latest tag:', data.get('tag_name'))

asset = None
for a in data.get('assets', []):
    name = a['name'].lower()
    if name.endswith('.zip') and 'win' in name and 'x86_64' in name:
        asset = a
        break

if asset:
    sz = asset['size'] / 1024 / 1024
    print(f'Selected: {asset["name"]} ({sz:.0f}MB)')
else:
    print('No matching x86_64 asset!')
    for a in data.get('assets', []):
        print(f'  Available: {a["name"]}')
