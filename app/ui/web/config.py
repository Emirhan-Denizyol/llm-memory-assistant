# app/ui/web/config.py
from pathlib import Path

# Bu dosyanın konumuna göre static dizinini çözüyoruz
BASE_DIR = Path(__file__).resolve().parent
UI_STATIC_DIR = BASE_DIR / "static"
UI_INDEX_FILE = UI_STATIC_DIR / "index.html"
