import pytest
from pathlib import Path
from ..base.scanner_test_base import NegativeScannerTest


class TestNegatives(NegativeScannerTest):
    """
    Negative test that scans the entire test_data directory and expects no unclaimed packages.
    If any unclaimed packages are found, they are reported as false positives that need to be fixed.
    """

    @pytest.fixture
    def test_file(self):
        return str(Path(__file__).parent / "test_data")
    
    def test_scanner_negative(self, test_file):
        """Override to provide more detailed failure information for comprehensive test"""
        result = self.run_scanner(test_file)
        
        # If we find unclaimed packages, provide detailed information
        if result["unclaimed_packages"]:
            error_msg = f"Found {len(result['unclaimed_packages'])} false positive(s):\n"
            for i, package in enumerate(result["unclaimed_packages"], 1):
                error_msg += f"\n{i}. Package '{package['name']}' in {package['file']} "
                error_msg += f"(scan_type: {package['scan_type']}, lines {package['start_line']}-{package['end_line']})\n"
                error_msg += f"   Code: {package['code_snippet'][:100]}{'...' if len(package['code_snippet']) > 100 else ''}\n"
            
            pytest.fail(error_msg)
        
        print(f"Negative test passed - no false positives found in {test_file}") 