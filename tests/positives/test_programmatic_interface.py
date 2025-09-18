import pytest
import time
import threading
import tempfile
import os
from pathlib import Path
from confusion_hunter.scanner import setup_scanner
from confusion_hunter.models.models import ScanResult

class TestProgrammaticInterface:
    """Test the programmatic interface to ensure it works without hanging in containerized environments"""
    
    @pytest.fixture
    def test_dir(self):
        return str(Path(__file__).parent / "test_data" / "requirements_python")
    
    @pytest.fixture
    def timeout_seconds(self):
        """Maximum time to allow for scan completion"""
        return 60
    
    def test_programmatic_interface_basic(self, test_dir, timeout_seconds):
        """Test the basic programmatic interface like the user is doing"""
        print(f"\n[TEST] Testing programmatic interface with {test_dir}")
        
        start_time = time.time()
        
        # Setup scanner
        scanner = setup_scanner(project_root=test_dir)
        
        # Run scan of the whole repository
        findings = scanner.find_config_files()
        assert len(findings) > 0, "Should find at least one configuration file"
        print(f"[TEST] Found {len(findings)} configuration files")
        
        # Run scan based on the findings
        unclaimed_packages = scanner.scan_files(findings)
        print(f"[TEST] Found {len(unclaimed_packages)} unclaimed packages")
        
        # Format the resulting data
        results = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)
        
        end_time = time.time()
        scan_duration = end_time - start_time
        
        print(f"[TEST] Scan completed in {scan_duration:.2f} seconds")
        
        # Verify the scan completed within reasonable time
        assert scan_duration < timeout_seconds, f"Scan took too long: {scan_duration:.2f}s > {timeout_seconds}s"
        
        # Verify we got expected results
        assert len(results.findings) > 0, "Should have findings"
        assert len(results.unclaimed_packages) > 0, "Should have unclaimed packages"
        
        # Verify we can convert to dict format
        result_dict = results.to_dict()
        assert "findings" in result_dict, "Should have findings in dict"
        assert "unclaimed_packages" in result_dict, "Should have unclaimed packages in dict"
        assert len(result_dict["findings"]) > 0, "Should have findings in dict"
        assert len(result_dict["unclaimed_packages"]) > 0, "Should have unclaimed packages in dict"
    
    def test_programmatic_interface_with_timeout(self, test_dir, timeout_seconds):
        """Test the programmatic interface with explicit timeout to catch hanging"""
        print(f"\n[TEST] Testing programmatic interface with timeout protection")
        
        result = [None]
        exception = [None]
        
        def run_scan():
            try:
                scanner = setup_scanner(project_root=test_dir)
                findings = scanner.find_config_files()
                unclaimed_packages = scanner.scan_files(findings)
                result[0] = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)
            except Exception as e:
                exception[0] = e
        
        # Run the scan in a separate thread with timeout
        thread = threading.Thread(target=run_scan)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        # Check if thread completed
        if thread.is_alive():
            pytest.fail(f"Scan hung and did not complete within {timeout_seconds} seconds")
        
        # Check for exceptions
        if exception[0]:
            raise exception[0]
        
        # Verify we got results
        assert result[0] is not None, "Scan should return results"
        assert len(result[0].findings) > 0, "Should have findings"
        assert len(result[0].unclaimed_packages) > 0, "Should have unclaimed packages"
        
        print(f"[TEST] Scan completed successfully within timeout")
    
    def test_programmatic_interface_multiple_calls(self, test_dir, timeout_seconds):
        """Test multiple sequential calls to ensure no resource leaks or hanging"""
        print(f"\n[TEST] Testing multiple sequential programmatic calls")
        
        results = []
        
        for i in range(3):
            print(f"[TEST] Running scan #{i+1}")
            start_time = time.time()
            
            scanner = setup_scanner(project_root=test_dir)
            findings = scanner.find_config_files()
            unclaimed_packages = scanner.scan_files(findings)
            result = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)
            
            end_time = time.time()
            scan_duration = end_time - start_time
            
            print(f"[TEST] Scan #{i+1} completed in {scan_duration:.2f} seconds")
            
            # Each scan should complete quickly
            assert scan_duration < timeout_seconds, f"Scan #{i+1} took too long: {scan_duration:.2f}s"
            
            results.append(result)
        
        # All scans should produce the same results
        for i in range(1, len(results)):
            assert len(results[i].findings) == len(results[0].findings), \
                f"Scan #{i+1} produced different number of findings"
            assert len(results[i].unclaimed_packages) == len(results[0].unclaimed_packages), \
                f"Scan #{i+1} produced different number of unclaimed packages"
        
        print(f"[TEST] All {len(results)} scans completed successfully")
    
    def test_programmatic_interface_concurrent_calls(self, test_dir, timeout_seconds):
        """Test concurrent calls to ensure thread safety"""
        print(f"\n[TEST] Testing concurrent programmatic calls")
        
        results = [None] * 3
        exceptions = [None] * 3
        
        def run_scan(index):
            try:
                scanner = setup_scanner(project_root=test_dir)
                findings = scanner.find_config_files()
                unclaimed_packages = scanner.scan_files(findings)
                results[index] = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)
            except Exception as e:
                exceptions[index] = e
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_scan, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        start_time = time.time()
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for i, thread in enumerate(threads):
            thread.join(timeout=timeout_seconds)
            if thread.is_alive():
                pytest.fail(f"Concurrent scan #{i+1} hung and did not complete within {timeout_seconds} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print(f"[TEST] All concurrent scans completed in {total_duration:.2f} seconds")
        
        # Check for exceptions
        for i, exception in enumerate(exceptions):
            if exception:
                raise exception
        
        # Verify all scans completed successfully
        for i, result in enumerate(results):
            assert result is not None, f"Concurrent scan #{i+1} should return results"
            assert len(result.findings) > 0, f"Concurrent scan #{i+1} should have findings"
            assert len(result.unclaimed_packages) > 0, f"Concurrent scan #{i+1} should have unclaimed packages"
        
        print(f"[TEST] All {len(results)} concurrent scans completed successfully")
    
    def test_programmatic_interface_empty_directory(self, timeout_seconds):
        """Test scanning an empty directory doesn't hang"""
        print(f"\n[TEST] Testing programmatic interface with empty directory")
        
        # Create a temporary empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"[TEST] Using temporary directory: {temp_dir}")
            
            start_time = time.time()
            
            scanner = setup_scanner(project_root=temp_dir)
            findings = scanner.find_config_files()
            unclaimed_packages = scanner.scan_files(findings)
            result = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)
            
            end_time = time.time()
            scan_duration = end_time - start_time
            
            print(f"[TEST] Empty directory scan completed in {scan_duration:.2f} seconds")
            
            # Should complete quickly even with no files
            assert scan_duration < timeout_seconds, f"Empty directory scan took too long: {scan_duration:.2f}s"
            
            # Should have no findings or unclaimed packages
            assert len(result.findings) == 0, "Empty directory should have no findings"
            assert len(result.unclaimed_packages) == 0, "Empty directory should have no unclaimed packages"
            
            print(f"[TEST] Empty directory scan completed successfully")
    
    def test_programmatic_interface_sarif_output(self, test_dir, timeout_seconds):
        """Test that SARIF output generation works without hanging"""
        print(f"\n[TEST] Testing SARIF output generation")
        
        start_time = time.time()
        
        scanner = setup_scanner(project_root=test_dir)
        findings = scanner.find_config_files()
        unclaimed_packages = scanner.scan_files(findings)
        result = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)
        
        # Generate SARIF output
        sarif_output = result.to_sarif()
        
        end_time = time.time()
        scan_duration = end_time - start_time
        
        print(f"[TEST] SARIF generation completed in {scan_duration:.2f} seconds")
        
        # Verify the scan completed within reasonable time
        assert scan_duration < timeout_seconds, f"SARIF generation took too long: {scan_duration:.2f}s"
        
        # Verify SARIF structure
        assert "$schema" in sarif_output, "Should have SARIF schema"
        assert "version" in sarif_output, "Should have SARIF version"
        assert "runs" in sarif_output, "Should have SARIF runs"
        assert len(sarif_output["runs"]) > 0, "Should have at least one run"
        
        print(f"[TEST] SARIF output generation completed successfully") 