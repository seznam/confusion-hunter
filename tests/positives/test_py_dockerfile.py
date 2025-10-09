import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestDockerfilePythonScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "dockerfile_pip")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "dockerfile", "path": "Dockerfile", "type": "python"},
                {"file_type": "dockerfile", "path": "Dockerfile", "type": "javascript"},

                {"file_type": "dockerfile", "path": "Dockerfile.2", "type": "python"},
                {"file_type": "dockerfile", "path": "Dockerfile.2", "type": "javascript"},

                {"file_type": "dockerfile", "path": "Dockerfile.gpu", "type": "python"},
                {"file_type": "dockerfile", "path": "Dockerfile.gpu", "type": "javascript"},

                {"file_type": "dockerfile", "path": "Dockerfile.fp", "type": "python"},
                {"file_type": "dockerfile", "path": "Dockerfile.fp", "type": "javascript"},
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-h", "scan_type": "python-pip", "start_line": 3, "end_line": 3, "language": "python"},
                {"name": "unclaimed-package-i", "scan_type": "python-pip", "start_line": 7, "end_line": 7, "language": "python"},
                {"name": "unclaimed-package-l", "scan_type": "python-pip", "start_line": 10, "end_line": 10, "language": "python"},
                {"name": "unclaimed-package-q2", "scan_type": "python-pip", "start_line": 13, "end_line": 13, "language": "python"},
                {"name": "unclaimed-package-m", "scan_type": "python-pip", "start_line": 16, "end_line": 16, "language": "python"},
                {"name": "unclaimed-package-r2", "scan_type": "python-pip", "start_line": 22, "end_line": 22, "language": "python"},
                {"name": "unclaimed-package-n", "scan_type": "python-pip", "start_line": 25, "end_line": 25, "language": "python"},
                {"name": "unclaimed-package-o", "scan_type": "python-pip", "start_line": 29, "end_line": 29, "language": "python"},
                {"name": "unclaimed-package-p", "scan_type": "python-pip", "start_line": 33, "end_line": 33, "language": "python"},
                {"name": "another-library", "scan_type": "python-pip", "start_line": 35, "end_line": 37, "language": "python"},
                {"name": "testing-library", "scan_type": "python-pip", "start_line": 35, "end_line": 37, "language": "python"},
                {"name": "unclaimed-package-j", "scan_type": "python-pip", "start_line": 35, "end_line": 37, "language": "python"},
                {"name": "unclaimed-package-q", "scan_type": "python-pip", "start_line": 27, "end_line": 27, "language": "python"},
                {"name": "unclaimed-package-r", "scan_type": "python-pip", "start_line": 28, "end_line": 28, "language": "python"},
                {"name": "unclaimed-package-u", "scan_type": "python-pip", "start_line": 32, "end_line": 41, "language": "python"},
                {"name": "unclaimed-org-project-bootstrap", "scan_type": "python-pip", "start_line": 24, "end_line": 28, "language": "python"}
            ]
        }
