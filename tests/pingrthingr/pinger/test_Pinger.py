import pytest
import asyncio

from icmplib import Host
from pathlib import Path
from json import load, JSONDecodeError
from typing import List, Tuple
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
def mocked_pinger(mocker, ping_response, request):
    def _mocked_pinger(testcase: str = "just_one_good") -> Tuple[Pinger, Tuple[int, int], Mock]:
        ping_reponse_value, callback_response = ping_response(testcase)
        mocker.patch(
            "pingrthingr.pinger.pinger.async_multiping", return_value=ping_reponse_value
        )
        callback_mock = Mock()
        pinger = Pinger(
            targets=["8.8.8.8"], count=1, timeout=1, cb=callback_mock, start_running=True
        )
        return pinger, callback_response, callback_mock

    return _mocked_pinger


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
async def test_Pinger(mocker, ping_response, test_case, mocked_pinger):
    pinger, callback_response, callback_mock = mocked_pinger(test_case)
    await asyncio.sleep(0.1)  # Allow the Pinger to initialize
    assert callback_mock.called, "Callback should be called after pinging"
    args, kwargs = callback_mock.call_args
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

class TestPingerStartPauseResumeDestroy():

    @pytest.mark.asyncio
    async def test_start(self, mocked_pinger):
        pinger, callback_response, callback_mock = mocked_pinger()  
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        assert callback_mock.called, "Callback should be called after pinging"
        assert len(asyncio.all_tasks(loop=pinger.loop)) == 1, "There should be one task in the loop when running"

    @pytest.mark.asyncio
    async def test_pause_and_restart(self, mocked_pinger):
        pinger, callback_response, callback_mock = mocked_pinger() 
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        pinger.run(False)
        callback_mock.reset_mock()
        await asyncio.sleep(0.2)  # Wait longer than the ping interval
        assert not callback_mock.called, "Callback should not be called when paused"
        assert pinger.pinger_coroutine == None, "Pinger coroutine should be None when paused"
        assert len(asyncio.all_tasks(loop=pinger.loop)) == 0, "There should be no tasks in the loop when paused"
        pinger.run(True)
        await asyncio.sleep(0.1)  # Allow the Pinger to restart
        assert callback_mock.called, "Callback should be called after resuming"
        assert len(asyncio.all_tasks(loop=pinger.loop)) == 1, "There should be one task in the loop when resumed"
    
    @pytest.mark.asyncio
    async def test_destroy(self, mocked_pinger):
        pinger, callback_response, callback_mock = mocked_pinger() 
        await asyncio.sleep(0.1)  # Allow the Pinger to initialize
        del(pinger)
        callback_mock.reset_mock()
        await asyncio.sleep(0.2)  # Wait longer than the ping interval
        assert not callback_mock.called, "Callback should not be called after destroy"
