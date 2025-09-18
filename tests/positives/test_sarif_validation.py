import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List
import pytest
from sarif_pydantic import Sarif
from pydantic import ValidationError
from ..base.scanner_test_base import ScannerTestBase


class TestSarifValidation(ScannerTestBase):
    """Test suite for SARIF output validation"""
    
    def run_scanner(self, target_path: str) -> Dict:
        """Run the scanner on a test directory and return the SARIF output"""
        result = subprocess.run(
            ["confusion-hunter", "--stdout", "--relative", target_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Scanner failed: {result.stderr}"
        
        # Find the SARIF output in the stdout
        output_lines = result.stdout.strip().split('\n')
        sarif_output = output_lines[-1]
        
        print(f"\n=== SARIF Output for {target_path} ===")
        print(sarif_output)
        print("=" * 50)
        
        try:
            return json.loads(sarif_output)
        except json.JSONDecodeError as e:
            print(f"Failed to parse SARIF output: {sarif_output}")
            print(f"Full output: {result.stdout}")
            raise e

    @pytest.fixture
    def test_data_directories(self):
        """Dynamically discover all test data directories"""
        test_data_path = Path(__file__).parent / "test_data"
        return [str(d) for d in test_data_path.iterdir() if d.is_dir()]

    @pytest.mark.parametrize("test_dir_name", [
        "pipfile",
        "requirements_python", 
        "poetry_lock",
        "uv_lock",
        "pyproject",
        "package_json",
        "pomxml",
        "build_gradle",
        "dockerfile_pip",
        "dockerfile_npm",
        "install_requirements",
        "gitlab-ci",
        "scripts"
    ])
    def test_sarif_output_validation(self, test_dir_name):
        """Test that SARIF output is valid for each test data directory"""
        test_dir = Path(__file__).parent / "test_data" / test_dir_name
        
        # Skip if test directory doesn't exist
        if not test_dir.exists():
            pytest.skip(f"Test directory {test_dir} does not exist")
        
        # Run the scanner and get SARIF output
        sarif_data = self.run_scanner(str(test_dir))
        
        # Validate basic SARIF structure
        self.assert_basic_sarif_structure(sarif_data)
        
        # Validate using sarif-pydantic
        try:
            sarif_log = Sarif.model_validate(sarif_data)
            print(f"SARIF validation successful for {test_dir_name}")
        except ValidationError as e:
            pytest.fail(f"SARIF validation failed for {test_dir_name}: {e}")
    
    def assert_basic_sarif_structure(self, sarif_data: Dict):
        """Assert that SARIF output has the correct basic structure"""
        # Check top-level required fields
        assert "$schema" in sarif_data, "Missing $schema field"
        assert "version" in sarif_data, "Missing version field"
        assert "runs" in sarif_data, "Missing runs field"
        
        # Check schema URL
        expected_schema = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/schemas/sarif-schema-2.1.0.json"
        assert sarif_data["$schema"] == expected_schema, f"Invalid schema URL: {sarif_data['$schema']}"
        
        # Check version
        assert sarif_data["version"] == "2.1.0", f"Invalid SARIF version: {sarif_data['version']}"
        
        # Check runs structure
        assert isinstance(sarif_data["runs"], list), "runs should be a list"
        assert len(sarif_data["runs"]) >= 1, "runs should contain at least one run"
        
        # Check first run structure
        run = sarif_data["runs"][0]
        assert "tool" in run, "Missing tool field in run"
        assert "results" in run, "Missing results field in run"
        
        # Check tool structure
        tool = run["tool"]
        assert "driver" in tool, "Missing driver field in tool"
        
        driver = tool["driver"]
        assert "name" in driver, "Missing name field in driver"
        assert "rules" in driver, "Missing rules field in driver"
        assert driver["name"] == "Dep-Conf-Scanner", f"Invalid driver name: {driver['name']}"
        
        # Check results structure
        results = run["results"]
        assert isinstance(results, list), "results should be a list"
        
        # If there are results, validate their structure
        for result in results:
            self.assert_result_structure(result)
    
    def assert_result_structure(self, result: Dict):
        """Assert that a SARIF result has the correct structure"""
        assert "ruleId" in result, "Missing ruleId in result"
        assert "level" in result, "Missing level in result"
        assert "message" in result, "Missing message in result"
        assert "locations" in result, "Missing locations in result"
        
        # Check message structure
        message = result["message"]
        assert "text" in message, "Missing text in message"
        
        # Check locations structure
        locations = result["locations"]
        assert isinstance(locations, list), "locations should be a list"
        assert len(locations) >= 1, "locations should contain at least one location"
        
        # Check first location
        location = locations[0]
        assert "physicalLocation" in location, "Missing physicalLocation in location"
        
        physical_location = location["physicalLocation"]
        assert "artifactLocation" in physical_location, "Missing artifactLocation"
        assert "region" in physical_location, "Missing region"
        
        # Check artifact location
        artifact_location = physical_location["artifactLocation"]
        assert "uri" in artifact_location, "Missing uri in artifactLocation"
        
        # Check that URI doesn't start with / (SARIF compliance)
        uri = artifact_location["uri"]
        assert not uri.startswith("/"), f"URI should not start with /: {uri}"
        
        # Check region
        region = physical_location["region"]
        assert "startLine" in region, "Missing startLine in region"
        assert "endLine" in region, "Missing endLine in region"
        assert isinstance(region["startLine"], int), "startLine should be an integer"
        assert isinstance(region["endLine"], int), "endLine should be an integer"
        assert region["startLine"] > 0, "startLine should be positive"
        assert region["endLine"] >= region["startLine"], "endLine should be >= startLine"
    
    def test_sarif_empty_results(self):
        """Test SARIF output when no unclaimed packages are found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an empty requirements.txt
            empty_req_file = os.path.join(temp_dir, "requirements.txt")
            with open(empty_req_file, "w") as f:
                f.write("# Empty requirements file\n")
            
            # Run scanner on empty directory
            sarif_data = self.run_scanner(temp_dir)
            
            # Should still be valid SARIF even with no results
            self.assert_basic_sarif_structure(sarif_data)
            
            # Validate with sarif-pydantic
            try:
                sarif_log = Sarif.model_validate(sarif_data)
                print("SARIF validation successful for empty results")
            except ValidationError as e:
                pytest.fail(f"SARIF validation failed for empty results: {e}")
            
            # Check that results array is empty
            results = sarif_data["runs"][0]["results"]
            assert len(results) == 0, "Results should be empty for directory with no unclaimed packages"