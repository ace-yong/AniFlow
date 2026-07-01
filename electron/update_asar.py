import struct, json, os, hashlib

asar_path = 'E:/vibecode/project/ganmelingo/electron/aniflow-20260701234004/win-unpacked/resources/app.asar'
out_path = asar_path

source_map = {
    'main.js': 'E:/vibecode/project/ganmelingo/electron/main.js',
    'renderer/app.js': 'E:/vibecode/project/ganmelingo/electron/renderer/app.js',
    'renderer/index.html': 'E:/vibecode/project/ganmelingo/electron/renderer/index.html',
}

def align4(x):
    return x + ((4 - (x % 4)) % 4)

with open(asar_path, 'rb') as f:
    raw = bytearray(f.read())

json_str_len = struct.unpack('<I', raw[12:16])[0]
json_str = raw[16:16+json_str_len].decode('utf-8')
old_header = json.loads(json_str)

data_offset = align4(16 + json_str_len)

# Extract file data
def collect_entries(d, prefix=''):
    entries = []
    for k, v in d.items():
        if isinstance(v, dict):
            if 'files' in v:
                entries.extend(collect_entries(v['files'], prefix+k+'/'))
            elif 'offset' in v:
                off = data_offset + sum(int(x) for x in v['offset'].split())
                entries.append({'path': prefix+k, 'size': v['size'], 'offset': off})
    return entries

entries = collect_entries(old_header.get('files', {}))
file_data = {}
for e in entries:
    file_data[e['path']] = bytes(raw[e['offset']:e['offset']+e['size']])

# Override with source files
for path, src in source_map.items():
    if os.path.exists(src):
        with open(src, 'rb') as f:
            file_data[path] = bytes(f.read())
        print(f'Updated: {path} ({len(file_data[path])} bytes)')

# Build new header tree
def build_tree():
    tree = {'files': {}}
    for path in sorted(file_data.keys()):
        parts = path.split('/')
        cur = tree['files']
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                data = file_data[path]
                h = hashlib.sha256(data).hexdigest()
                cur[part] = {
                    'size': len(data),
                    'offset': '0',
                    'integrity': {
                        'algorithm': 'SHA256',
                        'hash': h,
                        'blockSize': 4194304,
                        'blocks': [h]
                    }
                }
            else:
                if part not in cur:
                    cur[part] = {'files': {}}
                cur = cur[part]['files']
    return tree

new_header = build_tree()

# Calculate offsets
curr = 0
for path in sorted(file_data.keys()):
    data = file_data[path]
    parts = path.split('/')
    cur = new_header['files']
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            cur[part]['offset'] = str(curr)
        else:
            cur = cur[part]['files']
    curr += align4(len(data))

# Build pickle format
header_json = json.dumps(new_header, separators=(',', ':')).encode('utf-8')
header_payload_size = align4(4 + len(header_json))
header_pickle = struct.pack('<I', header_payload_size)
header_pickle += struct.pack('<I', len(header_json))
header_pickle += header_json
header_pickle += b'\x00' * (header_payload_size - 4 - len(header_json))

size_pickle = struct.pack('<I', 4) + struct.pack('<I', len(header_pickle))

data_start = align4(len(size_pickle) + len(header_pickle))
new_raw = bytearray()
new_raw.extend(size_pickle)
new_raw.extend(header_pickle)
while len(new_raw) < data_start:
    new_raw.append(0)

for path in sorted(file_data.keys()):
    new_raw.extend(file_data[path])
    while len(new_raw) % 4 != 0:
        new_raw.append(0)

with open(out_path, 'wb') as f:
    f.write(bytes(new_raw))

print(f'Written: {len(new_raw)} bytes')
print(f'Old asar: {len(raw)} bytes')

# Verify
with open(out_path, 'rb') as f:
    v = f.read()
js_len = struct.unpack('<I', v[12:16])[0]
v_json = v[16:16+js_len].decode('utf-8')
vh = json.loads(v_json)
print('Files in new asar:')
def print_files(d, p=''):
    for k, v in d.items():
        if isinstance(v, dict) and 'files' in v:
            print_files(v['files'], p+k+'/')
        elif 'offset' in v:
            print(f'  {p}{k}: size={v["size"]}')
print_files(vh.get('files', {}))
