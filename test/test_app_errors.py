"""Tests for app-layer error behavior used by CLI and Discord integrations."""

import pytest
import requests

from swgoh_helper.app import AppExecutionError, KyrotechAnalysisApp


def test_handle_request_error_raises_app_execution_error():
    """Request failures should raise domain errors instead of exiting the process."""
    app = KyrotechAnalysisApp.__new__(KyrotechAnalysisApp)

    with pytest.raises(AppExecutionError, match="Error fetching data:"):
        app._handle_request_error(requests.exceptions.RequestException("boom"))


def test_handle_general_error_raises_app_execution_error():
    """General failures should raise domain errors instead of exiting the process."""
    app = KyrotechAnalysisApp.__new__(KyrotechAnalysisApp)

    with pytest.raises(AppExecutionError, match="Error: boom"):
        app._handle_general_error(ValueError("boom"))
