import sys

with open('fotw/web/fotw-detail.js', 'rb') as f:
    raw = f.read()

# Check BOM
if raw[:3] == b'\xef\xbb\xbf':
    print('WARNING: UTF-8 BOM detected!')
else:
    print('No BOM')

# Check for null bytes or other problematic chars
for i in range(min(len(raw), 500)):
    b = raw[i]
    if b == 0:
        print(f'NULL byte at position {i}')
    if b < 9 or (b > 13 and b < 32 and b != 27):
        print(f'Control char at {i}: {b}')

# Try decoding as UTF-8
try:
    content = raw.decode('utf-8')
    print('UTF-8 decode OK, length:', len(content))
except Exception as e:
    print('UTF-8 decode error:', e)

# Check fotw.js too
print('\n--- fotw.js ---')
with open('fotw/web/fotw.js', 'rb') as f:
    raw2 = f.read()
if raw2[:3] == b'\xef\xbb\xbf':
    print('WARNING: UTF-8 BOM detected!')
else:
    print('No BOM')
try:
    content2 = raw2.decode('utf-8')
    print('UTF-8 decode OK, length:', len(content2))
except Exception as e:
    print('UTF-8 decode error:', e)

# Check CSS
print('\n--- fotw.css ---')
with open('fotw/web/fotw.css', 'rb') as f:
    raw3 = f.read()
if raw3[:3] == b'\xef\xbb\xbf':
    print('WARNING: UTF-8 BOM detected!')
else:
    print('No BOM')
try:
    content3 = raw3.decode('utf-8')
    print('UTF-8 decode OK, length:', len(content3))
except Exception as e:
    print('UTF-8 decode error:', e)
