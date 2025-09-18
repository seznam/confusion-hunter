import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

# Temporarily disabled module 

# class TestGradleBuildKtsScanner(PositiveScannerTest):

#     @pytest.fixture
#     def test_dir(self):
#         return str(Path(__file__).parent / "test_data" / "kts")

#     @pytest.fixture
#     def expected_output(self):
#         return {
#             "findings": [
#                 {"file_type": "buildgradle", "path": "build.gradle.kts", "type": "java"}
#             ],
#             "unclaimed_packages": [
#                 {"name": "cz.example-company.cileni:cid-utils", "scan_type": "gradle-buildgradle", "start_line": 62, "end_line": 62},
#                 {"name": "cz.example-company.cileni:consent-utils_$scalaVersion", "scan_type": "gradle-buildgradle", "start_line": 63, "end_line": 63},
#                 {"name": "cz.example-company.cileni:flibble_$scalaVersion", "scan_type": "gradle-buildgradle", "start_line": 64, "end_line": 64},
#                 {"name": "cz.example-company.cileni:java-utils", "scan_type": "gradle-buildgradle", "start_line": 67, "end_line": 67},
#                 {"name": "cz.example-company.cileni:sdhit-utils_$scalaVersion", "scan_type": "gradle-buildgradle", "start_line": 70, "end_line": 70},
#                 {"name": "com.example-company.project:project-urldewaste", "scan_type": "gradle-buildgradle", "start_line": 73, "end_line": 73},
#                 {"name": "com.example-company.project:util", "scan_type": "gradle-buildgradle", "start_line": 74, "end_line": 74},
#                 {"name": "cz.example-company.cileni.certik:certik", "scan_type": "gradle-buildgradle", "start_line": 77, "end_line": 77}
#             ]
#         }