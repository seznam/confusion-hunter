import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestNPMScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "package_json")


    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "package_json", "path": "package.json", "type": "javascript"}
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-h1", "scan_type": "js-package-json"},
                {"name": "unclaimed-package-i1", "scan_type": "js-package-json"},
                {"name": "unclaimed-package-j1", "scan_type": "js-package-json"},
                {"name": "unclaimed-package-k1", "scan_type": "js-package-json"},
                {"name": "unclaimed-package-l1", "scan_type": "js-package-json"},
                {"name": "unclaimed-package-m1", "scan_type": "js-package-json"}
            ]
        }
