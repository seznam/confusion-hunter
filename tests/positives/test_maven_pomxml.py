import pytest
from pathlib import Path
from ..base.scanner_test_base import PositiveScannerTest

# Temporarily disabled module 

# class TestMavenPomXmlScanner(PositiveScannerTest):

#     @pytest.fixture
#     def test_dir(self):
#         return str(Path(__file__).parent / "test_data" / "pomxml")

#     @pytest.fixture
#     def expected_output(self):
#         return {
#             "findings": [
#                 {"file_type": "pomxml", "path": "pom.xml", "type": "java"}
#             ],
#             "unclaimed_packages": [
#                 {"name": "cz.example-company:protobuf", "scan_type": "maven-pomxml", "start_line": 419, "end_line": 438},
#                 {"name": "cz.example-company:lib", "scan_type": "maven-pomxml", "start_line": 419, "end_line": 438}
#             ]
#         }