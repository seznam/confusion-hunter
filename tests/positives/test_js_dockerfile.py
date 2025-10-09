import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestDockerfileNPMScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "dockerfile_npm")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "dockerfile", "path": "Dockerfile", "type": "python"},
                {"file_type": "dockerfile", "path": "Dockerfile", "type": "javascript"},
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-h", "scan_type": "js-npm", "language": "javascript"},
                {"name": "unclaimed-package-i", "scan_type": "js-npm", "language": "javascript"},
                {"name": "unclaimed-package-j", "scan_type": "js-npm", "language": "javascript"},
                {"name": "@testorg/unclaimed-package-k", "scan_type": "js-npm", "language": "javascript"}
            ]
        }