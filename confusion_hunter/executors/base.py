from abc import ABC, abstractmethod
from typing import List
from ..models.models import FileFinding, PackageFinding
import os
import asyncio
import concurrent.futures
import threading
import time

class TimeoutError(Exception):
    """Custom timeout exception"""
    pass

def simple_timeout(func, timeout_seconds=300):
    """Simple timeout wrapper using threading"""
    def wrapper(*args, **kwargs):
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            # Thread is still running, it timed out
            raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    return wrapper

class BaseExecutor(ABC):
    """Base class for all file executors"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root

    def _read_file(self, file_finding: FileFinding) -> str:
        """
        Read the file content
        """
        try:
            file_path = os.path.join(self.project_root, file_finding.path)
            with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            print(f"Error scanning file {file_finding.path}: File not found")
            return ""
        except PermissionError:
            print(f"Error scanning file {file_finding.path}: Permission denied")
            return ""
        except Exception as e:
            print(f"Error scanning file {file_finding.path}: {str(e)}")
            return ""

    @abstractmethod
    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """
        Check if this executor should scan the given file.
        
        Args:
            file_finding: The file finding to check
            
        Returns:
            True if this executor should scan the file, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan a file for unclaimed packages asynchronously.
        
        Args:
            file_finding: The file finding to scan
            
        Returns:
            A list of package findings
        """
        raise NotImplementedError("Subclasses must implement this method")

    def scan_file(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Synchronous version of scan_file with timeout protection
        """
        def _run_scan():
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in an event loop, we need to run in a new thread
                    # to avoid "RuntimeError: asyncio.run() cannot be called from a running event loop"
                    def run_in_thread():
                        # Create a new event loop for each scan to avoid singleton issues
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(self.scan_file_async(file_finding))
                        finally:
                            new_loop.close()
                    
                    # Use ThreadPoolExecutor to run the async code in a separate thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        return future.result()
                except RuntimeError:
                    # No event loop running, safe to create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(self.scan_file_async(file_finding))
                    finally:
                        loop.close()
            except Exception as e:
                print(f"Error scanning file {file_finding.path}: {e}")
                return []
        
        try:
            # Apply timeout wrapper
            return simple_timeout(_run_scan, timeout_seconds=300)()
        except TimeoutError:
            print(f"Scanning file {file_finding.path} timed out")
            return []
        except Exception as e:
            print(f"Error scanning file {file_finding.path}: {e}")
            return []
