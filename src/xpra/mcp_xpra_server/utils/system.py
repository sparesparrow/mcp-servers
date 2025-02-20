import os
import shutil
import subprocess
from typing import Optional

def get_xpra_binary() -> str:
    """Locate the xpra binary in the system."""
    common_paths = [
        "/usr/bin/xpra",
        "/usr/local/bin/xpra",
        os.path.expanduser("~/.local/bin/xpra")
    ]
    
    for path in common_paths:
        if os.path.isfile(path):
            return path
            
    xpra_path = shutil.which("xpra")
    if xpra_path:
        return xpra_path
        
    raise RuntimeError("Xpra binary not found in system. Please install xpra first.")

def check_system_dependencies() -> Optional[str]:
    """Check if all required system dependencies are installed."""
    try:
        subprocess.run(["xpra", "--version"], 
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE,
                     check=True)
    except subprocess.CalledProcessError:
        return "xpra is not installed or not working correctly"
    except FileNotFoundError:
        return "xpra binary not found in PATH"
        
    try:
        subprocess.run(["xset", "q"], 
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "X server not running or DISPLAY not set"
        
    # Add check for required system memory
    try:
        import psutil
        if psutil.virtual_memory().available < 1024 * 1024 * 512:  # 512MB
            return "Insufficient system memory"
    except ImportError:
        pass  # Optional check
    
    # Add X11 socket check
    if not os.path.exists("/tmp/.X11-unix"):
        return "X11 socket directory not found"
    
    return None