"""SUU-160: render.yaml — Render 무료 플랜이 main merge마다 백엔드를 다시 켠다. 파일만 검사, 배포 확인은 사람."""
import re
from pathlib import Path

RENDER = Path(__file__).parents[2] / "render.yaml"
ENV_KEYS = ["PYTHONPATH", "SUPABASE_URL", "SUPABASE_SECRET_KEY", "OPENAI_API_KEY", "ISAACUS_API_KEY", "FRONTEND_ORIGIN"]


def text():
    return RENDER.read_text(encoding="utf-8")


def test_render_yaml_is_one_free_python_web_service():
    t = text()
    assert re.search(r"^\s*-\s*type:\s*web\s*$", t, re.M)
    assert re.search(r"^\s*runtime:\s*python\s*$", t, re.M)
    assert re.search(r"^\s*plan:\s*free\s*$", t, re.M)


def test_render_yaml_installs_root_requirements_and_starts_uvicorn_on_health():
    t = text()
    assert re.search(r"^\s*buildCommand:\s*pip install -r requirements\.txt\s*$", t, re.M)
    assert re.search(r"^\s*startCommand:\s*uvicorn app\.main:app --host 0\.0\.0\.0 --port \$PORT\s*$", t, re.M)
    assert re.search(r"^\s*healthCheckPath:\s*/health\s*$", t, re.M)


def test_render_yaml_lists_every_env_var_and_pythonpath_reaches_backend_and_rag():
    t = text()
    for key in ENV_KEYS:
        assert re.search(rf"^\s*-\s*key:\s*{key}\s*$", t, re.M), key
    # 비밀값은 파일에 없다. 대시보드에서 넣는다(sync: false)
    for key in ENV_KEYS[1:5]:
        assert re.search(rf"key:\s*{key}\s*\n\s*sync:\s*false", t), key
    # app.main이 ecfr_* 모듈을 import 하려면 두 폴더가 PYTHONPATH에 있어야 한다
    m = re.search(r"key:\s*PYTHONPATH\s*\n\s*value:\s*['\"]?([^'\"\n]+)", t)
    assert m and set(m.group(1).split(":")) == {"[3] backend", "[2] db/pipeline/5_rag"}
