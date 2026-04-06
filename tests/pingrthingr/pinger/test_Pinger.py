import pytest
import asyncio

from icmplib import Host
from pathlib import Path
from json import load, JSONDecodeError
from threading import enumerate as threading_enumerate
from typing import List, Tuple, Callable
from unittest.mock import Mock

from pingrthingr.pinger import Pinger

base_path = Path(__file__).parent


@pytest.fixture
def ping_response():
    def _ping_response(testcase: str) -> Tuple[List[Host], Tuple[int, int]]:
        results = []
        try:
            with open(f"{base_path}/resources/responses/{testcase}.json", "r") as f:
                data = load(f)
                for d in data["ping_response"]:
                    results.append(Host(**d))
        except FileNotFoundError:
            pytest.fail(
                f"Test case {testcase} not found. Please ensure the file {base_path}/resources/responses/{testcase}.json exists."
            )
        except (JSONDecodeError, TypeError) as e:
            pytest.fail(f"Error parsing test case {testcase}: {e}")

        return results, data["callback_response"]

    return _ping_response


@pytest.fixture
def mocked_pinger(mocker, ping_response):
    pingers = []

    def _mocked_pinger(
        testcase: str = "just_one_good", targets: List[str] = ["127.0.0.1"], cb: Callable | None = Mock(), start_running: bool = True
    ) -> Tuple[Pinger, Tuple[int, int], Mock | Callable |None]:
        ping_reponse_value, callback_response = ping_response(testcase)
        mocker.patch(
            "pingrthingr.pinger.pinger.async_multiping", return_value=ping_reponse_value
        )
        pinger = Pinger(
            targets=targets,
            count=1,
            timeout=1,
            cb=cb,
            start_running=start_running,
        )
        pingers.append(pinger)  # Keep a reference to allow cleanup
        return pinger, callback_response, cb

    yield _mocked_pinger

    for pinger in pingers:
        pinger.stop()  # Ensure all pingers are stopped after tests
        del pinger  # Remove reference to allow garbage collection


class TestPingerResponses:

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "test_case",
        [
            "all_success",
            "all_failures",
            "one_failure",
            "just_one_bad",
            "just_one_good",
            "no_results",
            "one_outlier",
            "two_outliers",
        ],
    )
    async def test_Pinger(self, test_case, mocked_pinger):
        _, callback_response, callback_mock = mocked_pinger(test_case)
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert callback_mock.called, "Callback should be called after pinging"
        args, _ = callback_mock.call_args
        assert (
            len(args) == 2
        ), "Callback should be called with two arguments: latency and loss"

        for i, arg in enumerate(args):
            assert isinstance(
                arg, (float, type(None))
            ), "Callback arguments should be numbers or None"
            if arg is not None:
                assert arg >= 0, f"Callback argument {i} should be non-negative, got {arg}"
            assert arg == pytest.approx(
                callback_response[i]
            ), f"Expected callback argument {i} to be approximately {callback_response[i]}, got {arg}"
    
    @pytest.mark.asyncio
    async def test_pinger_no_targets(self, mocked_pinger):
        _, callback_response, callback_mock = mocked_pinger(targets=[])
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert not callback_mock.called, "Callback should not be called with no targets"

    @pytest.mark.asyncio
    async def test_pinger_invalid_targets(self, mocked_pinger):
        with pytest.raises(ValueError, match="Invalid IP address: invalid_ip"):
             mocked_pinger(targets=["invalid_ip"])

    @pytest.mark.asyncio
    async def test_pinger_no_cb(self, mocked_pinger):
        pinger, _, _ = mocked_pinger(cb=None)
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert pinger.cb is None
        # No callback to check, just ensure no exceptions are raised

class TestPingerStartPauseResumeDestroy:

    @pytest.mark.asyncio
    async def test_start(self, mocked_pinger):
        pinger, _, callback_mock = mocked_pinger()
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert callback_mock.called, "Callback should be called after pinging"
        assert (
            len(asyncio.all_tasks(loop=pinger._loop)) == 1
        ), "There should be one task in the loop when running"

    @pytest.mark.asyncio
    async def test_start_paused(self, mocked_pinger):
        starting_thread_count = len(threading_enumerate())
        pinger, _, callback_mock = mocked_pinger(start_running=False)
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert not callback_mock.called, "Callback should not be called when paused"
        assert (
            pinger._pinger_coroutine == None
        ), "Pinger coroutine should be None when paused"
        assert (
            pinger._loop is None or not pinger._loop.is_running()
        ), "Event loop should be stopped when paused"
        assert (
            len(threading_enumerate()) == starting_thread_count
        ), "Pinger thread should not be running when paused"

    @pytest.mark.asyncio
    async def test_pause_and_restart(self, mocked_pinger):
        starting_thread_count = len(threading_enumerate())
        pinger, _, callback_mock = mocked_pinger()
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert (
            len(threading_enumerate()) == starting_thread_count + 1
        ), "There should be one additional thread for the Pinger"
        pinger.run(False)
        callback_mock.reset_mock()
        await asyncio.sleep(0.2)  # Wait longer than the ping interval
        assert not callback_mock.called, "Callback should not be called when paused"
        assert (
            pinger._pinger_coroutine is None
        ), "Pinger coroutine should be None when paused"
        assert (
            pinger._loop is None or not pinger._loop.is_running()
        ), "Event loop should be stopped when paused"
        assert (
            len(threading_enumerate()) == starting_thread_count
        ), "Pinger thread should be stopped when paused"
        pinger.run(True)
        await asyncio.sleep(0.1)  # Allow the Pinger to restart
        assert callback_mock.called, "Callback should be called after resuming"

    @pytest.mark.asyncio
    async def test_start_when_started(self, mocked_pinger):
        pinger, _, callback_mock = mocked_pinger()
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        starting_thread_count = len(threading_enumerate())
        assert callback_mock.called, "Callback should be called after pinging"
        callback_mock.reset_mock()
        pinger.run(True)  # Should not have any effect since it's already running
        await asyncio.sleep(0.1)  # Allow time for any unintended effects
        assert (
            pinger._pinger_coroutine is not None
        ), "Pinger coroutine should still be set after calling run(True) when already running"
        assert (
            not pinger._pinger_coroutine.done()
        ), "Ping task should still be running after calling run(True) when already running"
        assert (
            len(threading_enumerate()) == starting_thread_count
        ), "There should be no new threads after calling run(True) while already running"

    @pytest.mark.asyncio
    async def test_stop_when_stopped(self, mocked_pinger):
        pinger, _, callback_mock = mocked_pinger(start_running=False)
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert not callback_mock.called, "Callback should not be called when paused"
        pinger.stop()  # Should not raise an exception even if already stopped
        assert (
            not callback_mock.called
        ), "Callback should not be called after stopping when already stopped"
        assert (
            pinger._pinger_coroutine is None
        ), "Pinger coroutine should be None after stopping when already stopped"
