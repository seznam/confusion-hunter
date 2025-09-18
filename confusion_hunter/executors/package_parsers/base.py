from abc import ABC, abstractmethod
from typing import Tuple, List
from typing_extensions import TypeAlias
import re

from dataclasses import dataclass

Line: TypeAlias = Tuple[str, Tuple[int, int]]

@dataclass
class DetectedCommand:
    packages: List[str]
    line_numbers: Tuple[int, int]
    snippet: str


class PackageParser(ABC):
    """
    Abstract base class for detecting package installations.
    """
    
    @abstractmethod
    def get_packages(self, cmd: str) -> list[DetectedCommand]:
        """Return the clean list of package names (no versions / flags) and the start and end line numbers of the command."""
        raise NotImplementedError("Subclasses must implement this method")

    def _merge_backslash_lines(self, cmd: str) -> list[Line]:
        """
        Merge lines with backslash into one line
        """
        lines = cmd.splitlines()
        merged_lines = []
        current = ""
        start_line = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not current:
                start_line = i

            if stripped.endswith("\\"):
                current += stripped[:-1] + " "
            else:
                current += stripped
                if current:
                    merged_lines.append((current, (start_line + 1, i + 1)))
                    current = ""

        if current:
            merged_lines.append((current, (start_line + 1, len(lines))))

        return merged_lines


    def _split_shell_chain(self, line: str) -> list[str]:
        # old return:
        # return re.split(r"""\s*(?:&&|;'")\s*""", line)
        # it caused False positives for file: tests/integration/test_data/dockerfile_pip/Dockerfile.fp
        return re.split(r'\s*(?:;|&&|\|\|)\s*', line)
