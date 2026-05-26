import os
from pathlib import Path

import pytest


PROVIDER_PROOF_FIXTURE_TEST_ENV = "RUN_PROVIDER_PROOF_ARTIFACT_FIXTURE_TESTS"


def pytest_collection_modifyitems(items):
    if os.environ.get(PROVIDER_PROOF_FIXTURE_TEST_ENV) == "1":
        return

    skip_concrete_provider_fixtures = pytest.mark.skip(
        reason=(
            "provider proof output fixture freshness tests are local-artifact "
            f"checks; set {PROVIDER_PROOF_FIXTURE_TEST_ENV}=1 to run them"
        )
    )
    for item in items:
        test_file = Path(str(item.fspath)).name
        if test_file in {
            "test_blocker_proof_packets_browser.py",
            "test_blocker_snapshot_consistency.py",
        } or (
            test_file == "test_provider_proof_plan_cli.py"
            and item.name.startswith("test_concrete_")
        ):
            item.add_marker(skip_concrete_provider_fixtures)
