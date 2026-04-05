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
    def _ping_response(testcase: str) -> Tuple[List[Host], Tuple[int,int]]:
        results = []
        try:
            with open(f"{base_path}/resources/responses/{testcase}.json", "r") as f:
                data = load(f)
                for d in data['ping_response']:
                    results.append(Host(**d))
        except FileNotFoundError:
            pytest.fail(
                f"Test case {testcase} not found. Please ensure the file {base_path}/resources/responses/{testcase}.json exists."
            )
        except (JSONDecodeError, TypeError) as e:
            pytest.fail(f"Error parsing test case {testcase}: {e}")

        return results,data['callback_response'] 

    return _ping_response

@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", ["all_success","all_failures", "one_failure"])
async def test_Pinger(mocker, ping_response, test_case):
    ping_reponse_value, callback_response = ping_response(test_case)
    mocker.patch("pingrthingr.pinger.pinger.async_multiping", return_value=ping_reponse_value)
    callback_mock = Mock()
    Pinger(targets=['8.8.8.8'], count=1, timeout=1,cb=callback_mock, start_running=True)
    await asyncio.sleep(0.1)  # Allow the Pinger to initialize
    callback_mock.assert_called_with(*callback_response)  # Check if the callback was called at least once