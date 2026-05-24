import argparse
from uuid import UUID

from all_about_llms.cli import _worker_scheduler_request_from_args
from all_about_llms.contracts import WorkerProfileExecutionMode


def test_worker_scheduler_cli_builds_scoped_request():
    run_id = "11111111-1111-4111-8111-111111111111"
    request = _worker_scheduler_request_from_args(
        argparse.Namespace(
            max_profiles=7,
            run_id=run_id,
            execution_mode="autonomous_pass",
        )
    )

    assert request.max_profiles == 7
    assert request.run_id == UUID(run_id)
    assert request.execution_mode == WorkerProfileExecutionMode.AUTONOMOUS_PASS


def test_worker_scheduler_cli_keeps_global_defaults_when_unscoped():
    request = _worker_scheduler_request_from_args(
        argparse.Namespace(
            max_profiles=25,
            run_id=None,
            execution_mode=None,
        )
    )

    assert request.max_profiles == 25
    assert request.run_id is None
    assert request.execution_mode is None
