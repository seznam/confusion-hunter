import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestPyprojectScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "pyproject")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "pyproject", "path": "pyproject.toml", "type": "python"}
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-z", "scan_type": "python-pyproject", "language": "python"}
            ]
        }