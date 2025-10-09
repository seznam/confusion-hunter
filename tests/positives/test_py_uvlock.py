import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestUvLockScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "uv_lock")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "uvlock", "path": "uv.lock", "type": "python"}
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-org-service-api-base", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-service-common", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-service-configutils", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-configutils", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-service-backupclient", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-service-auth", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-exceptiontools", "scan_type": "python-uvlock", "language": "python"},
                {"name": "unclaimed-org-python-utils", "scan_type": "python-uvlock", "language": "python"}
            ]
        }