"""Test utilities for Kitty terminal graphics support."""

import base64
import sys
from .protocol import serialize_gr_command, is_kitty_terminal


def test_kitty_graphics() -> None:
    """
    Test Kitty terminal graphics support by displaying a small test image.
    """
    if not is_kitty_terminal():
        print("This test must be run in a Kitty terminal (TERM=xterm-kitty).", file=sys.stderr)
        return

    # 10x10 green PNG data
    dummy_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAAXNSR0IArs4c6QAAADBJREFUGJVjYICC+P//PwMDBYaHMMDADyMDQ7gBIISJgREMQ4E7QBCDDQxDxWCMCQYAR/k0Hn0SMGIAAAAASUVORK5CYII="
    dummy_png_data = base64.b64decode(dummy_png_b64)

    print("Attempting to display a 10x10 green PNG pixel using Kitty graphics protocol...", file=sys.stderr)
    sys.stdout.buffer.write(serialize_gr_command(a='T', f=100, m=0, payload=base64.b64encode(dummy_png_data)))
    sys.stdout.buffer.flush()
    print("\nCheck if a green pixel appeared above this line.", file=sys.stderr)


def main():
    """Test Kitty terminal graphics support."""
    test_kitty_graphics()


if __name__ == '__main__':
    main() 