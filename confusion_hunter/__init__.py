"""
Confusion Hunter - Lightweight scanner for spotting unclaimed dependencies before attackers do.

Protects your projects from supply-chain attacks by catching dependency confusion vectors.
"""

from .scanner import setup_scanner, run_scanner, check_unclaimed_packages
from .models.models import ScanResult
from .detectors import *
from .executors import *

__version__ = "0.1.0"
__author__ = "Seznam Security Team"
__email__ = "security@firma.seznam.cz "
__license__ = "MIT"

__all__ = ['setup_scanner', 'ScanResult', 'run_scanner', 'check_unclaimed_packages', 'detectors', 'executors']
