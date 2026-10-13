"""Deploy DawaDrishti to a free Hugging Face Space (Gradio SDK on CPU basic; Docker Spaces are paid).

    pip install huggingface_hub
    python deploy/huggingface.py              # asks for a WRITE token (typing is hidden)
    python deploy/huggingface.py --dry-run    # build the upload folder only

Uploads the last COMMITTED version (git archive HEAD) + the freshly built web app + deploy/hf_app.py as app.py,
with deploy/requirements-space.txt as requirements.txt, and forces CPU-basic hardware (ZeroGPU forces Python 3.10).
"""
from __future__ import annotations

import argparse
import getpass
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRADIO_VERSION = "6.30.0"
HEADER = f"""---
title: DawaDrishti
emoji: 💊
colorFrom: red
colorTo: blue
sdk: gradio
sdk_version: {GRADIO_VERSION}
python_version: "3.11"
app_file: app.py
pinned: false
license: mit
short_description: A national memory of medicine-quality failures
---

"""


def run(cmd, cwd=None):
    print("  $", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def stage(dst: Path) -> str:
    web = ROOT / "web"
    if not (web / "node_modules").exists():
        run(["npm", "install"], cwd=web)
    run(["npm", "run", "build"], cwd=web)
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        print("  note: uncommitted changes are NOT deployed (only the last commit + the web build).")
    tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", "HEAD"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(dst, filter="data")
    shutil.copytree(web / "dist", dst / "web" / "dist", dirs_exist_ok=True)
    shutil.copy(ROOT / "deploy" / "hf_app.py", dst / "app.py")
    shutil.copy(ROOT / "deploy" / "requirements-space.txt", dst / "requirements.txt")
    readme = dst / "README.md"
    readme.write_text(HEADER + readme.read_text())
    return sha


def ensure_free_hardware(api, repo_id: str):
    """A Space created on GPU hardware (e.g. ZeroGPU) cannot be moved to free CPU without a PRO plan.
    If the existing Space is on paid/GPU hardware, offer to delete it so it can be re-created on cpu-basic."""
    try:
        rt = api.get_space_runtime(repo_id)
    except Exception:
        return                                   # the Space does not exist yet: create_repo makes it on cpu-basic
    hw = rt.requested_hardware or rt.hardware
    if hw in (None, "cpu-basic"):
        return
    files = [f.rfilename for f in (api.space_info(repo_id).siblings or [])]
    print(f"\n  {repo_id} is set to '{hw}', which a free account cannot switch to free CPU.")
    print(f"  It contains {len(files)} file(s): {', '.join(files[:6])}{' ...' if len(files) > 6 else ''}")
    if input("  Type DELETE to delete it and re-create it on free CPU (anything else stops): ").strip() != "DELETE":
        sys.exit("Stopped. Nothing was changed.")
    api.delete_repo(repo_id, repo_type="space")
    print("  deleted; re-creating on cpu-basic")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default="dawadrishti")
    ap.add_argument("--user")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dst = Path(tempfile.mkdtemp(prefix="dawadrishti-space-"))
    sha = stage(dst)
    print(f"staged commit {sha} in {dst}")
    if a.dry_run:
        print(f"test it: cd {dst} && python app.py  (http://localhost:7860)")
        return
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("Install the uploader into this Python first:  python -m pip install huggingface_hub")
    token = os.environ.get("HF_TOKEN") or getpass.getpass("Paste your Hugging Face WRITE token (typing is hidden): ").strip()
    api = HfApi(token=token)
    me = api.whoami()["name"]
    repo_id = f"{a.user or me}/{a.space}"
    print(f"logged in as {me}; deploying to {repo_id}")
    ensure_free_hardware(api, repo_id)
    api.create_repo(repo_id, repo_type="space", space_sdk="gradio", space_hardware="cpu-basic", exist_ok=True)
    api.upload_folder(folder_path=str(dst), repo_id=repo_id, repo_type="space", commit_message=f"Deploy {sha}", delete_patterns=["*"])
    rt = api.get_space_runtime(repo_id)
    if rt.requested_hardware != "cpu-basic":
        print(f"switching hardware {rt.requested_hardware} -> cpu-basic (free)")
        try:
            api.request_space_hardware(repo_id, "cpu-basic")
        except Exception as e:  # free accounts cannot downgrade a GPU Space; it must be re-created
            sys.exit(f"Could not switch to free CPU ({e}).\nDelete the Space at https://huggingface.co/spaces/{repo_id}/settings "
                     "(bottom of the page) and run this script again; it will be re-created on free CPU.")
    shutil.rmtree(dst, ignore_errors=True)
    sub = repo_id.lower().replace("/", "-").replace("_", "-").replace(".", "-")
    print(f"\nUploaded. Build log: https://huggingface.co/spaces/{repo_id}\nLive app:  https://{sub}.hf.space")


if __name__ == "__main__":
    main()
