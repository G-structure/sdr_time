import sys
from base64 import standard_b64encode
import os
import base64

def serialize_gr_command(**cmd):
    payload = cmd.pop('payload', None)
    cmd_str = ','.join(f'{k}={v}' for k, v in cmd.items())
    ans = []
    w = ans.append
    w(b'\033_G')
    w(cmd_str.encode('ascii'))
    if payload:
        w(b';')
        w(payload)
    w(b'\033\\')
    return b''.join(ans)

def write_chunked(**cmd):
    data = standard_b64encode(cmd.pop('data'))
    # For this simple test, assume data fits in one chunk
    m = 0 # No more data
    sys.stdout.buffer.write(serialize_gr_command(payload=chunk, m=m, **cmd))
    sys.stdout.buffer.flush()
    # cmd.clear() # Not strictly needed for single chunk a=T

# 10x10 green PNG
dummy_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAAXNSR0IArs4c6QAAADBJREFUGJVjYICC+P//PwMDBYaHMMDADyMDQ7gBIISJgREMQ4E7QBCDDQxDxWCMCQYAR/k0Hn0SMGIAAAAASUVORK5CYII="
dummy_png_data = base64.b64decode(dummy_png_b64)

def main():
    """Test Kitty terminal graphics support."""
    if os.environ.get('TERM') != 'xterm-kitty':
        print("This test script must be run in a Kitty terminal (TERM=xterm-kitty).", file=sys.stderr)
        sys.exit(1)

    print("Attempting to display a 10x10 green PNG pixel using Kitty graphics protocol...", file=sys.stderr)
    # write_chunked(a='T', f=100, data=dummy_png_data)
    # Simpler for single chunk, small data
    sys.stdout.buffer.write(serialize_gr_command(a='T', f=100, m=0, payload=base64.standard_b64encode(dummy_png_data)))
    sys.stdout.buffer.flush()
    print("\nCheck if a red pixel appeared above this line.", file=sys.stderr)


if __name__ == '__main__':
    main()

