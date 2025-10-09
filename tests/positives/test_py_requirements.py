import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestRequirementsPythonScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "requirements_python")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "requirements", "path": "devrequirements-test.txt", "type": "python"}
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-a", "scan_type": "python-requirements", "start_line": 7, "end_line": 7, "language": "python"},
                {"name": "unclaimed-package-b", "scan_type": "python-requirements", "start_line": 8, "end_line": 8, "language": "python"},
                {"name": "unclaimed-package-c", "scan_type": "python-requirements", "start_line": 9, "end_line": 9, "language": "python"},
                {"name": "unclaimed-package-d", "scan_type": "python-requirements", "start_line": 12, "end_line": 12, "language": "python"},
                {"name": "unclaimed-package-e", "scan_type": "python-requirements", "start_line": 13, "end_line": 13, "language": "python"},
                {"name": "unclaimed-package-f", "scan_type": "python-requirements", "start_line": 14, "end_line": 14, "language": "python"},
                {"name": "unclaimed-package-g", "scan_type": "python-requirements", "start_line": 18, "end_line": 18, "language": "python"}
            ]
        }