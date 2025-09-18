import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List
import pytest
from abc import ABC, abstractmethod


class ScannerTestBase(ABC):
    """Base test class for scanner tests with common functionality"""
    
    @property
    def scanner_path(self) -> str:
        """Path to the scanner script"""
        return str(Path(__file__).parents[2] / "src" / "scanner.py")
    
    def run_scanner(self, target_path: str) -> Dict:
        """Run the scanner on a test directory and return the JSON output"""
        result = subprocess.run(
            ["confusion-hunter", "--stdout", "--relative", "--raw", target_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Scanner failed: {result.stderr}"
        
        # Find the JSON output in the stdout
        # The JSON output is the last line of the output
        output_lines = result.stdout.strip().split('\n')
        json_output = output_lines[-1]
        
        print("\n=== Scanner Output ===")
        print(result.stdout)
        print("\n=== JSON Output ===")
        print(json_output)
        print("===================\n")
        
        try:
            return json.loads(json_output)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON output: {json_output}")
            print(f"Full output: {result.stdout}")
            raise e
    
    def assert_findings_structure(self, findings: List[Dict]):
        """Assert that findings have the correct structure"""
        required_fields = {"file_type", "path", "type"}

        for finding in findings:
            assert all(field in finding for field in required_fields), \
                f"Missing required fields in finding: {finding}"

    def assert_unclaimed_packages_structure(self, unclaimed_packages: List[Dict]):
        """Assert that unclaimed packages have the correct structure"""
        required_fields = {
            "code_snippet", "start_line", "end_line", "file", "message",
            "name", "report_type", "scan_type", "severity"
        }

        for package in unclaimed_packages:
            assert all(field in package for field in required_fields), \
                f"Missing required fields in package: {package}"

    def _match_object(self, actual: Dict, expected: Dict) -> bool:
        """
        Helper to check if all fields in expected are present and equal in actual.
        """
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if actual_value != expected_value:
                return False
        return True


class PositiveScannerTest(ScannerTestBase):
    """Base class for positive tests - expecting specific findings"""
    
    def assert_unclaimed_packages_content(self, unclaimed_packages: List[Dict], expected_packages: List[Dict]):
        """
        Asserts that for each expected unclaimed package, there is a matching entry in the actual unclaimed packages list.
        Only the keys specified in each expected package are checked.
        """
        for expected in expected_packages:
            match_found = any(self._match_object(actual, expected) for actual in unclaimed_packages)
            assert match_found, f"Expected unclaimed package not found or mismatched: {expected}"

    def assert_findings_content(self, findings: List[Dict], expected_findings: List[Dict]):
        """Assert that findings have the correct content"""
        for expected in expected_findings:
            match_found = any(self._match_object(actual, expected) for actual in findings)
            assert match_found, f"Expected finding not found or mismatched: {expected}"

    def test_scanner_positive(self, test_dir, expected_output):
        """Test scanning expecting specific findings"""
        # Run the scanner
        result = self.run_scanner(test_dir)
        
        # Verify findings
        self.assert_findings_structure(result["findings"])

        # Verify unclaimed packages
        self.assert_unclaimed_packages_structure(result["unclaimed_packages"])

        # Verify unclaimed packages content
        self.assert_unclaimed_packages_content(result["unclaimed_packages"], expected_output["unclaimed_packages"])
        
        # Check if the number of unclaimed packages is as expected
        assert len(result["unclaimed_packages"]) == len(expected_output["unclaimed_packages"])
        
        # Verify findings content
        self.assert_findings_content(result["findings"], expected_output["findings"])
        
        # Check if the number of findings is as expected
        assert len(result["findings"]) == len(expected_output["findings"])


class NegativeScannerTest(ScannerTestBase):
    """Base class for negative tests - expecting no findings"""
    
    def test_scanner_negative(self, test_file):
        """Test scanning expecting no findings (negative test)"""
        # Run the scanner
        result = self.run_scanner(test_file)
        
        # Assert no unclaimed packages are found
        assert result["unclaimed_packages"] == [], \
            f"Expected no unclaimed packages, but found: {result['unclaimed_packages']}"
        
        # Optionally, we might also want to assert no findings, 
        # but findings just indicate which files were scanned, so they might be OK
        print(f"Scan completed successfully for {test_file} - no unclaimed packages found") 