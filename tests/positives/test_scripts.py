import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

class TestScriptsScanner(PositiveScannerTest):

    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "scripts")


    @pytest.fixture
    def expected_output(self):
        return {
            "findings": [
                { "file_type": "script", "path": "script.sh", "type": "python" },
                { "file_type": "script", "path": "script.sh", "type": "javascript" },
                { "file_type": "script", "path": "placeholder.sh", "type": "python" },
                { "file_type": "script", "path": "placeholder.sh", "type": "javascript" },
            ],
            "unclaimed_packages": [
                {"name": "unclaimed-package-s2", "scan_type": "python-pip", "file": "script.sh", "language": "python"},
                {"name": "unclaimed-package-t2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"},
                {"name": "unclaimed-package-u2", "scan_type": "python-pip", "file": "script.sh", "language": "python"},
                {"name": "unclaimed-package-v2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"},
                {"name": "unclaimed-package-w2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"},
                {"name": "unclaimed-package-x2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"},
                {"name": "unclaimed-package-x2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"},
                {"name": "unclaimed-package-y2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"},
                {"name": "@testorg/unclaimed-package-z2", "scan_type": "js-npm", "file": "script.sh", "language": "javascript"}
            ]
        }
