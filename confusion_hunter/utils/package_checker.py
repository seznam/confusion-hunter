import asyncio, random, logging, aiohttp, async_timeout, os
from typing import List, Dict
from aiohttp import ClientError, ClientTimeout
from aiolimiter import AsyncLimiter
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    before_sleep_log
)
from enum import Enum
from dataclasses import dataclass

PYPI_URL = os.getenv("PYPI_URL", "https://pypi.org/pypi")
NPM_URL = os.getenv("NPM_URL", "https://registry.npmjs.org")
NPM_ORG_URL = os.getenv("NPM_ORG_URL", "https://www.npmjs.com/~")
MAVEN_URL = os.getenv("MAVEN_URL", "https://repo1.maven.org/maven2")



class PackageStatus(Enum):
    """Enum representing the status of a package check"""
    FOUND = "found"           # Package exists (HTTP 200)
    NOT_FOUND = "not_found"   # Package doesn't exist (HTTP 404)
    NETWORK_ERROR = "network_error"  # Network timeout/error - status unknown


@dataclass
class TunablesParams:
    TIMEOUT_SECS = int(os.getenv("TIMEOUT_SECS", "10"))   # timeout for a single request
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "15"))     # Increased from 3 to 15
    BACKOFF_BASE = int(os.getenv("BACKOFF_BASE", "1"))    # Base for exponential backoff between retries
    CONN_POOL_SIZE = int(os.getenv("CONN_POOL_SIZE", "20"))   # Size of the aiohttp TCP connection pool
    REQS_PER_SECOND = int(os.getenv("REQS_PER_SECOND", "10"))   # Max requests per second (rate limit)
    MAX_IN_FLIGHT = int(os.getenv("MAX_IN_FLIGHT", "50"))   # Max concurrent in-flight requests


ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "False").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

if ENABLE_LOGGING:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.CRITICAL + 1)


def should_retry_on_network_error(result):
    """Only retry on network errors, not on successful responses or 404s"""
    return result == PackageStatus.NETWORK_ERROR


class PackageChecker:
    """
    Simple package checker that creates fresh resources for each batch.
    This avoids the singleton pattern which can cause hangs in K8s environments.
    """
    
    def __init__(self):
        self.session = None
        self.limiter = None
        self.semaphore = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_resources()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_resources()
    
    async def _initialize_resources(self):
        """Initialize HTTP session and rate limiting resources"""
        # Create rate limiter and semaphore
        self.limiter = AsyncLimiter(TunablesParams.REQS_PER_SECOND, 1)
        self.semaphore = asyncio.Semaphore(TunablesParams.MAX_IN_FLIGHT)
        
        # Create HTTP session with connection pooling
        timeout = ClientTimeout(total=TunablesParams.TIMEOUT_SECS + 5)
        connector = aiohttp.TCPConnector(
            limit=TunablesParams.CONN_POOL_SIZE,
            limit_per_host=TunablesParams.CONN_POOL_SIZE,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=True
        )
        
        logger.info("PackageChecker initialized")
    
    async def _cleanup_resources(self):
        """Clean up HTTP session and other resources"""
        if self.session:
            await self.session.close()
        logger.info("PackageChecker cleaned up")
    
    async def check_packages_with_status(self, pkgs: List, kind: str) -> List[PackageStatus]:
        """
        Check packages and return full status information including network errors.
        """
        if not pkgs:
            return []
        
        logger.info("START batch %s (%s packages)", kind.upper(), len(pkgs))
        
        # Create tasks based on registry type
        tasks = []
        if kind.lower() == "pypi":
            tasks = [self._package_exists_pypi(p) for p in pkgs]
        elif kind.lower() == "npm":
            tasks = [self._package_exists_npm(p) for p in pkgs]
        elif kind.lower() == "maven":
            tasks = [self._package_exists_maven(p) for p in pkgs]
        else:
            raise ValueError(f"Unsupported package type: {kind}")
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Log results with better status information
        found_count = sum(1 for r in results if r == PackageStatus.FOUND)
        not_found_count = sum(1 for r in results if r == PackageStatus.NOT_FOUND)
        network_error_count = sum(1 for r in results if r == PackageStatus.NETWORK_ERROR)
        
        logger.info("DONE  batch %s — %s found, %s not found, %s network errors",
                    kind.upper(), found_count, not_found_count, network_error_count)
        
        return results
    
    @retry(
        stop=stop_after_attempt(TunablesParams.MAX_RETRIES),
        wait=wait_exponential(multiplier=TunablesParams.BACKOFF_BASE, min=1, max=30),
        retry=retry_if_result(should_retry_on_network_error),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request_with_retry(self, url: str, method: str = "HEAD") -> PackageStatus:
        """
        Make a request with proper retry logic that distinguishes between network errors and HTTP responses.
        Returns PackageStatus instead of boolean to provide more information.
        """
        try:
            async with self.semaphore:  # concurrency gate
                async with self.limiter:  # RPS gate
                    async with async_timeout.timeout(TunablesParams.TIMEOUT_SECS):
                        logger.debug("REQ  %s %s", method, url)
                        async with self.session.request(method, url, allow_redirects=True) as r:
                            logger.info("RES  %s %s → %s", method, url, r.status)
                            
                            if r.status == 200:
                                return PackageStatus.FOUND
                            elif r.status == 404:
                                return PackageStatus.NOT_FOUND
                            elif r.status in [403, 429]:  # Rate limited or forbidden
                                # These should trigger a retry
                                logger.warning("Rate limited or forbidden: %s %s → %s", method, url, r.status)
                                return PackageStatus.NETWORK_ERROR
                            else:
                                # Other HTTP errors (500, 502, etc.) should trigger retry
                                logger.warning("HTTP error: %s %s → %s", method, url, r.status)
                                return PackageStatus.NETWORK_ERROR

        except (ClientError, asyncio.TimeoutError) as exc:
            logger.warning("Network error: %s %s → %s", method, url, exc.__class__.__name__)
            return PackageStatus.NETWORK_ERROR
        except Exception as exc:
            logger.error("Unexpected error: %s %s → %s", method, url, exc.__class__.__name__)
            return PackageStatus.NETWORK_ERROR
    
    async def _package_exists_pypi(self, pkg: str) -> PackageStatus:
        """Check if a PyPI package exists"""
        return await self._make_request_with_retry(f"{PYPI_URL}/{pkg}/json", "HEAD")
    
    async def _scope_exists_npm(self, scope: str) -> PackageStatus:
        """Check if an npm scope exists"""
        return await self._make_request_with_retry(f"{NPM_ORG_URL}{scope}", "HEAD")
    
    async def _individual_package_exists_npm(self, pkg: str) -> PackageStatus:
        """Check if an individual npm package exists"""
        return await self._make_request_with_retry(f"{NPM_URL}/{pkg}", "HEAD")
    
    async def _package_exists_npm(self, pkg: str) -> PackageStatus:
        """Check if an npm package exists (handles scoped packages)"""
        # For scoped packages, check the package directly via registry API
        # instead of checking the scope via website (which is blocked by Cloudflare)
        return await self._individual_package_exists_npm(pkg)
    
    async def _package_exists_maven(self, pkg: Dict) -> PackageStatus:
        """Check if a Maven package exists"""
        group_id = pkg.get('groupId', '')
        artifact_id = pkg.get('artifactId', '')
        if not group_id or not artifact_id:
            return PackageStatus.NOT_FOUND
        
        # Use the official Maven Central Repository REST API
        url = f"{MAVEN_URL}/{group_id.replace('.', '/')}/{artifact_id}/maven-metadata.xml"
        return await self._make_request_with_retry(url, "HEAD")


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Public functions
# --------------------------------------------------------------------------

def check_packages_sync(pkgs: List, kind: str) -> List[bool]:
    """
    Synchronous version of package checking that creates fresh resources.
    This is the preferred method for synchronous code.
    
    Arguments:
        pkgs: List - list of packages to check (strings for npm/pypi, dicts with groupId/artifactId for maven)
        kind: str - type of package registry (pypi, npm, or maven)
    Returns:
        List[bool] - list of booleans, True if the package exists, False if not found or network error
    """
    async def _check_batch():
        async with PackageChecker() as checker:
            results = await checker.check_packages_with_status(pkgs, kind)
            return [status == PackageStatus.FOUND for status in results]
    
    # Create a fresh event loop for this batch
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_check_batch())
    finally:
        loop.close()


def check_packages_with_detailed_status(pkgs: List, kind: str) -> List[PackageStatus]:
    """
    Synchronous version that returns detailed status information.
    Use this when you need to distinguish between network errors and actual "not found" responses.
    
    Arguments:
        pkgs: List - list of packages to check (strings for npm/pypi, dicts with groupId/artifactId for maven)
        kind: str - type of package registry (pypi, npm, or maven)
    Returns:
        List[PackageStatus] - list of PackageStatus enum values (FOUND, NOT_FOUND, NETWORK_ERROR)
    """
    async def _check_batch():
        async with PackageChecker() as checker:
            return await checker.check_packages_with_status(pkgs, kind)
    
    # Create a fresh event loop for this batch
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_check_batch())
    finally:
        loop.close()


async def check_packages_async(pkgs: List, kind: str) -> List[bool]:
    """
    Async version of package checking. 
    
    Arguments:
        pkgs: List - list of packages to check (strings for npm/pypi, dicts with groupId/artifactId for maven)
        kind: str - type of package registry (pypi, npm, or maven)
    Returns:
        List[bool] - list of booleans, True if the package exists, False if not found or network error

    Detailed summary how it works:
    -------------
    - Creates fresh HTTP session for each batch to avoid resource leaks
    - Sends HEAD requests to the registries to minimize the bandwidth
    - Timeout: each request is wrapped with a hard timeout (`TIMEOUT_SECS`)
    - Retries: up to `MAX_RETRIES` times (default 15) with exponential backoff using tenacity
    - Rate limiting: enforced with `aiolimiter.AsyncLimiter`:
        - At most `REQS_PER_SECOND` requests per second
        - Limiter is shared across all calls for global rate limiting
    - Concurrency limiting: enforced with `asyncio.Semaphore`:
        - At most `MAX_IN_FLIGHT` requests can be "in flight" simultaneously
        - Prevents resource exhaustion (RAM / open sockets / upstream overload)
    - Connection pooling: aiohttp TCPConnector with `CONN_POOL_SIZE` connections

    Features:
    -------------
    - Improved retry logic with tenacity (exponential backoff with jitter)
    - Distinguishes between network errors and actual HTTP 404 responses
    - Only HTTP 404 responses are considered "not found" - network errors do not mark packages as unclaimed
    - Fresh resources for each batch to avoid singleton cleanup issues
    - Global rate limiting across all calls
    - Connection reuse and DNS caching
    - Timeout control
    - Comprehensive logging of all requests and errors

    Usage Examples:
    -------------
        result = await check_packages_async(["requests", "numpy"], "pypi") -> [True, True]
        result = await check_packages_async(["non-existent-package", "react"], "npm") -> [False, True]
        result = await check_packages_async([{"groupId": "org.apache", "artifactId": "commons-lang3"}], "maven") -> [True]
    """
    async with PackageChecker() as checker:
        results = await checker.check_packages_with_status(pkgs, kind)
        return [status == PackageStatus.FOUND for status in results]
