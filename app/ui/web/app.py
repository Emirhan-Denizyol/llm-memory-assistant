# app/ui/web/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from .config import UI_STATIC_DIR, UI_INDEX_FILE


def mount_react_ui(app: FastAPI, base_path: str = "/ui") -> None:
    """
    React ile build edilen frontend'i FastAPI üzerinde servis eder.

    Örnek kullanım (main.py içinde):
        from app.ui.web.app import mount_react_ui
        mount_react_ui(app, base_path="/ui")
    """

    # /ui/static altından JS/CSS gibi statik dosyalar
    app.mount(
        f"{base_path}/static",
        StaticFiles(directory=UI_STATIC_DIR),
        name="ui-static",
    )

    # /ui veya /ui/ path'ine gelen isteklerde index.html dön
    @app.get(base_path, response_class=HTMLResponse, include_in_schema=False)
    @app.get(f"{base_path}/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_react_app() -> HTMLResponse:
        if not UI_INDEX_FILE.exists():
            # Geliştirme ortamında build alınmamışsa uyarı mesajı dönelim
            return HTMLResponse(
                content=(
                    "<h1>UI build edilmemiş</h1>"
                    "<p>Önce <code>ui-frontend</code> klasöründe "
                    "<code>npm run build</code> çalıştırın.</p>"
                ),
                status_code=500,
            )

        html = UI_INDEX_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=html)
