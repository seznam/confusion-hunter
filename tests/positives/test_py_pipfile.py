import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestPipfilePythonScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "pipfile")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "pipfile", "path": "Pipfile", "type": "python"}
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-v", "scan_type": "python-pipfile", "start_line": 13, "end_line": 13, "language": "python"},
                {"name": "unclaimed-package-v2", "scan_type": "python-pipfile", "start_line": 14, "end_line": 14, "language": "python"},
                {"name": "unclaimed-package-v3", "scan_type": "python-pipfile", "start_line": 25, "end_line": 25, "language": "python"}
            ]
        }