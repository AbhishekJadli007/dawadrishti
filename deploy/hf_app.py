"""Hugging Face Spaces entry point (free "Gradio" SDK Space, CPU basic).

Hugging Face runs `python app.py` and routes the public URL to port 7860. We do not use Gradio's UI:
this starts the normal DawaDrishti FastAPI server (API + pre-built React app). The ERP database is
copied to /tmp first, because the Space's app folder may be read-only and the ERP desk writes to it.
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
live = Path("/tmp/dawadrishti/erp.sqlite")
if not live.exists():
    live.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "data" / "erp" / "erp.sqlite", live)
os.environ["DAWADRISHTI_ERP_DB"] = str(live)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=int(os.environ.get("GRADIO_SERVER_PORT", os.environ.get("PORT", "7860"))))
