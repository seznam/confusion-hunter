import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestGitlabCiScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "gitlab-ci")

    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                {"file_type": "gitlab-ci", "path": "gitlab-ci.yml", "type": "python"},
                {"file_type": "gitlab-ci", "path": "gitlab-ci.yml", "type": "javascript"},
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-v", "scan_type": "python-pip"},
                {"name": "unclaimed-package-v", "scan_type": "python-pip"},
                {"name": "unclaimed-package-v", "scan_type": "python-pip"},
                {"name": "unclaimed-package-v", "scan_type": "js-npm"}
            ]
        }
