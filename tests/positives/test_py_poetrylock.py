import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestPoetryLockScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "poetry_lock")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "poetrylock", "path": "poetry.lock", "type": "python"}
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-org-urllib3-client", "scan_type": "python-poetrylock", "language": "python"},
                {"name": "unclaimed-org-testtest", "scan_type": "python-poetrylock", "language": "python"},
                {"name": "unclaimed-org-python-metaserver-gendoc", "scan_type": "python-poetrylock", "language": "python"},
                {"name": "unclaimed-org-gridlogger", "scan_type": "python-poetrylock", "language": "python"},
                {"name": "unclaimed-org-imp-tornado", "scan_type": "python-poetrylock", "language": "python"}
            ]
        }