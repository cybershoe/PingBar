import logging

LOGGER = logging.getLogger(__name__)

import pytest
import asyncio
from threading import enumerate as threading_enumerate
from pingrthingr.updates.update_check import run_update_check
from httpx import HTTPError

@pytest.fixture
def mock_request(mocker):
    def _mock_request(status_code=200, json_data=None, raise_for_status=None):
        mock_response = mocker.Mock()
        mock_response.status_code = status_code
        mock_response.json = lambda: json_data or {}
        if raise_for_status:
            mock_response.raise_for_status.side_effect = raise_for_status
        else:
            mock_response.raise_for_status.return_value = None
        mocker.patch(
            "pingrthingr.updates.update_check.AsyncClient.get",
            return_value=mock_response,
        )
        return mock_response
    return _mock_request


# @pytest.fixture
# def callback_await():
#     future = asyncio.Future()

#     def callback(*args, **kwargs):
#         future.set_result((args, kwargs))

#     return callback, future


class TestUpdateCheck:

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "current_version_name, latest_version_tag, expected_new_version, expected_url, expected_error",
        [
            ("v0.1.0", "v1.0.0-release", "v1.0.0", "https://example.com/release", ""), # new version available
            ("v1.0.0", "v1.0.0-release", "", "", "v1.0.0 is the latest version."),  # up to date
            ("v1.2.3-beta", "v1.2.2-release", "", "", "v1.2.3-beta is the latest version."), # newer than latest
        ],
    )
    async def test_update_check_updates(self, mocker, mock_request, current_version_name, latest_version_tag, expected_new_version, expected_url, expected_error):
        # Mock the GitHub API response to return the same version as current
        mock_request(
            status_code=200,
            json_data={
                "tag_name": latest_version_tag,
                "html_url": expected_url,
            },
        )
        callback = mocker.MagicMock()

        run_update_check(current_version_name, callback, quiet=True)
        await asyncio.sleep(0.1)  # Wait for the thread to complete
        assert callback.called
        new_tag, repo_url, error, quiet = callback.call_args[0] 
        assert new_tag == expected_new_version
        assert repo_url == expected_url
        assert error == expected_error
        assert quiet is True

    @pytest.mark.asyncio
    async def test_update_check_http_error(self, mocker, mock_request):
        mock_request(raise_for_status=HTTPError("HTTP error occurred"))
        callback = mocker.MagicMock()
        run_update_check("v1.0.0", callback, quiet=True)
        await asyncio.sleep(0.1)  # Wait for the thread to complete
        assert callback.called
        new_tag, repo_url, error, quiet = callback.call_args[0] 
        assert new_tag == ""
        assert repo_url == ""
        assert "HTTP error occurred" in error
        assert quiet is True