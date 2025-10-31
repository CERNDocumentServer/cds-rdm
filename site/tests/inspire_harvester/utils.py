from unittest.mock import Mock, patch

from celery import current_app
from invenio_vocabularies.services.tasks import process_datastream


def mock_requests_get(
    url, mock_content, headers={"Accept": "application/json"}, stream=True
):
    mock_response = Mock()
    mock_response.status_code = 200
    if "files" in url:
        with open(
            "tests/inspire_harvester/data/inspire_file.bin",
            "rb",
        ) as f:
            mock_content = f.read()
            mock_response.content = mock_content
    else:
        mock_response.json.return_value = mock_content
    return mock_response


def run_harvester_mock(datastream_cfg, mock_content_function):
    """Process datastream."""
    with patch(
        "cds_rdm.inspire_harvester.reader.requests.get",
        side_effect=mock_content_function,
    ):
        process_datastream(config=datastream_cfg["config"])
        tasks = current_app.control.inspect()
        while True:
            if not tasks.scheduled():
                break
