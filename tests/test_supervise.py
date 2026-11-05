"""Supervisor lifecycle tests: no real subprocess, database or network."""
import signal
import subprocess
from unittest.mock import Mock
import pytest
from scripts import supervise


@pytest.fixture
def harness(monkeypatch):
    handlers = {}
    def register(sig, handler):
        previous = handlers.get(sig, signal.SIG_DFL)
        handlers[sig] = handler
        return previous
    monkeypatch.setattr(supervise.signal, 'signal', register)
    monkeypatch.delenv('OFFSITE_BACKUP_ENABLED', raising=False)
    spawn = Mock()
    monkeypatch.setattr(supervise.subprocess, 'Popen', spawn)
    monkeypatch.setattr(supervise.time, 'sleep', lambda _: None)
    return handlers, spawn


def child():
    process = Mock()
    process.poll.return_value = None
    process.returncode = None
    def terminated():
        process.poll.return_value = 0
    process.terminate.side_effect = terminated
    return process


def test_startup_failure_reaps_existing_api(harness):
    handlers, spawn = harness
    api = child()
    spawn.side_effect = [api, OSError('synthetic startup failure')]
    with pytest.raises(OSError, match='synthetic startup failure'):
        supervise.main()
    api.terminate.assert_called_once()
    api.wait.assert_called_once()
    api.kill.assert_not_called()
    assert all(h == signal.SIG_DFL for h in handlers.values())


def test_child_exit_stops_sibling_and_preserves_failure_code(harness):
    _, spawn = harness
    api, worker = child(), child()
    worker.poll.return_value = 7
    worker.returncode = 7
    spawn.side_effect = [api, worker]
    assert supervise.main() == 7
    api.terminate.assert_called_once()
    worker.terminate.assert_not_called()
    api.wait.assert_called_once()
    worker.wait.assert_called_once()


def test_sigterm_stops_children_and_escalates_after_deadline(harness, monkeypatch):
    handlers, spawn = harness
    api, worker = child(), child()
    spawn.side_effect = [api, worker]
    def stop(_):
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        api.poll.return_value = 0
        worker.poll.return_value = 0
    monkeypatch.setattr(supervise.time, 'sleep', stop)
    api.wait.side_effect = [subprocess.TimeoutExpired('synthetic', 25), None]
    assert supervise.main() == 0
    api.kill.assert_called_once()
    api.terminate.assert_called_once()
    worker.terminate.assert_called_once()
    assert api.wait.call_args_list[0].kwargs['timeout'] <= 25


def test_optional_backup_start_failure_also_reaps_both_children(harness, monkeypatch):
    _, spawn = harness
    monkeypatch.setenv('OFFSITE_BACKUP_ENABLED', 'true')
    api, worker = child(), child()
    spawn.side_effect = [api, worker, OSError('synthetic backup startup failure')]
    with pytest.raises(OSError):
        supervise.main()
    api.terminate.assert_called_once()
    worker.terminate.assert_called_once()
    assert [call.args[0][2] for call in spawn.call_args_list] == ['uvicorn', 'backend.worker', 'scripts.offsite_backup']


def test_signal_during_start_still_reaps_just_created_child(harness):
    handlers, spawn = harness
    api = child()
    def start(_):
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        return api
    spawn.side_effect = start
    assert supervise.main() == 0
    spawn.assert_called_once()
    api.terminate.assert_called_once()
    api.wait.assert_called_once()
