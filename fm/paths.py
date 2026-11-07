import os
from pathlib import Path

CLIENT_DIR = Path(os.environ.get(
    "FM_CLIENT_DIR",
    "/home/bazzite/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_forever_"))
