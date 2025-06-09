"""Kitty terminal graphics protocol utilities."""

import base64
import os
import sys
from io import BytesIO
from typing import Optional

import matplotlib.pyplot as plt


def serialize_gr_command(**cmd) -> bytes:
    """
    Serialize a graphics command for the kitty terminal.
    This follows the kitty graphics protocol.
    
    Args:
        **cmd: Command parameters as key-value pairs
        
    Returns:
        Serialized command as bytes
    """
    payload = cmd.pop('payload', None)
    cmd_str = ','.join(f'{k}={v}' for k, v in cmd.items())
    ans = []
    w = ans.append
    w(b'\033_G')  # Start graphics command
    w(cmd_str.encode('ascii'))
    if payload:
        w(b';')
        w(payload)
    w(b'\033\\')  # End graphics command
    return b''.join(ans)


def write_chunked(**cmd) -> None:
    """
    Write image data in chunks using the kitty graphics protocol.
    This allows sending larger images without hitting terminal buffer limits.
    
    Args:
        **cmd: Command parameters including 'data' key with image data
    """
    data = base64.b64encode(cmd.pop('data'))
    chunk_size = 4096
    
    # Preserve all command keys for the first chunk
    first_chunk_cmd_dict = {k: v for k, v in cmd.items() if k != 'data'}

    idx = 0
    while data:
        chunk, data = data[:chunk_size], data[chunk_size:]
        
        current_payload = chunk
        more_data_follows = 1 if data else 0
        
        if idx == 0:  # First chunk
            command_to_send = first_chunk_cmd_dict.copy()
            command_to_send['payload'] = current_payload
            command_to_send['m'] = more_data_follows
        else:  # Subsequent chunks - only 'm' and 'payload'
            command_to_send = {'m': more_data_follows, 'payload': current_payload}

        sys.stdout.buffer.write(serialize_gr_command(**command_to_send))
        sys.stdout.buffer.flush()
        idx += 1


def display_current_plt_figure_kitty_adapted(
    plt_instance: plt,
    print_error_func: Optional[callable] = None,
    image_id: int = 1,
    dpi: int = 75,
    suppress_errors: bool = True
) -> None:
    """
    Saves the current matplotlib figure to a buffer and displays it using Kitty graphics protocol.
    
    Args:
        plt_instance: Matplotlib pyplot instance
        print_error_func: Function to call for error messages
        image_id: Unique image ID for the terminal
        dpi: Image resolution
        suppress_errors: Whether to suppress error output
    """
    try:
        if not plt_instance:
            return

        buf = BytesIO()
        plt_instance.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0.01)
        buf.seek(0)
        png_data = buf.getvalue()
        
        if not png_data:
            return
            
        write_chunked(a='T', f=100, i=image_id, q=1, data=png_data)
    
    except Exception as e:
        if not suppress_errors and print_error_func:
            print_error_func(f"Error displaying figure: {e}")


def is_kitty_terminal() -> bool:
    """
    Check if the current terminal supports Kitty graphics protocol.
    
    Returns:
        True if running in Kitty terminal
    """
    return os.environ.get('TERM') == 'xterm-kitty' 