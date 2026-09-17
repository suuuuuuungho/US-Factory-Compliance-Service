"""SessionStart hook: worktree에 .env가 없으면 원본 저장소의 .env를 복사한다.

원본 폴더(.git이 진짜 폴더인 곳)에서는 아무것도 하지 않는다.
"""
import shutil
import subprocess
from pathlib import Path

cwd = Path.cwd()
if not (cwd / ".env").exists():
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, cwd=cwd).stdout.strip()
    src = (cwd / common).resolve().parent / ".env"
    if src.exists() and src.parent != cwd:
        shutil.copy(src, cwd / ".env")
        print(f".env copied from {src.parent}")
