"""SUU-68: register_release → load_release → publish_release를 순서대로 실행한다.

각 단계가 옳은지는 SUU-65/66/67에서 이미 검증했다. 여기서는 run_ecfr_ingest가
그 세 함수를 올바른 순서·인자로 부르고 release_id를 이어주는지만 확인한다.
adi_details_run.run처럼 함수를 키워드 인자로 주입해서 가짜로 바꿔치기한다.
"""
from pathlib import Path

from ecfr_ingest import run_ecfr_ingest

ROOT = Path("/fake/root")
AS_OF = "2026-09-10"
RELEASE_ID = "11111111-1111-1111-1111-111111111111"


class FakeClient:
    pass


def test_calls_register_load_publish_in_order_and_threads_the_release_id():
    calls: list[tuple] = []
    client = FakeClient()

    def fake_register_release(root, as_of, *, client):
        calls.append(("register", root, as_of, client))
        return RELEASE_ID

    def fake_load_release(root, as_of, release_id, *, client):
        calls.append(("load", root, as_of, release_id, client))

    def fake_publish_release(release_id, *, client):
        calls.append(("publish", release_id, client))

    result = run_ecfr_ingest(
        ROOT, AS_OF,
        client=client,
        register_release=fake_register_release,
        load_release=fake_load_release,
        publish_release=fake_publish_release,
    )

    assert result == RELEASE_ID
    assert calls == [
        ("register", ROOT, AS_OF, client),
        ("load", ROOT, AS_OF, RELEASE_ID, client),
        ("publish", RELEASE_ID, client),
    ]


def test_uses_the_real_functions_by_default():
    import ecfr_ingest

    assert ecfr_ingest.run_ecfr_ingest.__kwdefaults__["register_release"].__module__ == "ecfr_release"
    assert ecfr_ingest.run_ecfr_ingest.__kwdefaults__["load_release"].__module__ == "ecfr_load"
    assert ecfr_ingest.run_ecfr_ingest.__kwdefaults__["publish_release"].__module__ == "ecfr_publish"
