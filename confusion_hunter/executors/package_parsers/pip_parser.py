from __future__ import annotations

import io
import json
import os
import re
import shlex
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import bashlex
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    # Prefer pip's own parser for accurate option/positional splitting
    from pip._internal.commands.install import InstallCommand  # type: ignore
    _PIP_INSTALL_PARSER = InstallCommand("x", "x").parser
except Exception:
    _PIP_INSTALL_PARSER = None  # fallback path is conservative and FP-averse


# ====== Public types (kept compatible with your code) ======

LineSpan = Tuple[int, int]

@dataclass(frozen=True)
class DetectedCommand:
    packages: List[str]           # canonical (PEP-503) names, deduped, sorted
    line_numbers: LineSpan        # 1-based inclusive
    snippet: str                  # original command text for context


# ====== Core helpers ======

def _offset_to_line(text: str, offset: int) -> int:
    """Char-offset (0-based) -> 1-based line number."""
    return text.count("\n", 0, offset) + 1


def _iter_shell_commands(text: str) -> list[tuple[list[str], LineSpan, str]]:
    """
    Yield (argv_words, (start_line, end_line), snippet) for each shell *command* node.
    Uses bashlex NodeVisitor (no regex scanning).
    """
    try:
        roots = bashlex.parser.parse(text, convertpos=True)
    except Exception:
        # Fallback to regex-based parsing when bashlex fails
        return _iter_shell_commands_fallback(text)

    class _CmdVisitor(bashlex.ast.nodevisitor):
        def __init__(self, src: str):
            self.src = src
            self.items: list[tuple[list[str], LineSpan, str]] = []

        def visitcommand(self, node, parts):
            words = [p.word for p in parts if getattr(p, "kind", None) == "word"]
            s, e = getattr(node, "pos", (0, 0))
            start_line = _offset_to_line(self.src, s)
            end_line = _offset_to_line(self.src, e)
            snippet = self.src[s:e]
            
            # Check if this command contains multiple pip install patterns
            # This happens when line continuations join separate pip commands
            pip_commands = []
            i = 0
            
            while i < len(words):
                # Look for pip install patterns
                if i < len(words) - 1 and words[i] == "pip" and words[i + 1] == "install":
                    # Found "pip install"
                    cmd_start = i
                elif (i >= 3 and i < len(words) - 1 and 
                      words[i - 2] == "-m" and words[i - 1] == "pip" and words[i] == "install"):
                    # Found "python -m pip install"
                    # Look backwards for "python"
                    python_idx = i - 3
                    while python_idx >= 0 and not words[python_idx].startswith("python"):
                        python_idx -= 1
                    cmd_start = python_idx if python_idx >= 0 else i - 2
                else:
                    i += 1
                    continue
                
                # Found a pip install command, now find where it ends
                install_idx = i if words[i] == "install" else i + 1
                
                # Look for the next pip command or end of words
                next_pip_start = len(words)
                for j in range(install_idx + 1, len(words) - 1):
                    if (words[j] == "pip" and j + 1 < len(words) and words[j + 1] == "install") or \
                       (j >= 2 and words[j - 2] == "-m" and words[j - 1] == "pip" and words[j] == "install"):
                        next_pip_start = j
                        if words[j - 1] == "pip":
                            next_pip_start = j
                        elif j >= 3 and words[j - 3].startswith("python"):
                            next_pip_start = j - 3
                        break
                
                cmd_words = words[cmd_start:next_pip_start]
                if cmd_words:
                    pip_commands.append(cmd_words)
                
                i = next_pip_start
            
            if len(pip_commands) > 1:
                # Multiple pip commands found, add them separately
                for cmd_words in pip_commands:
                    self.items.append((cmd_words, (start_line, end_line), ' '.join(cmd_words)))
            else:
                # Single command or no pip install commands
                self.items.append((words, (start_line, end_line), snippet))
            return True

    v = _CmdVisitor(text)
    for r in roots:
        v.visit(r)
    return v.items


def _iter_shell_commands_fallback(text: str) -> list[tuple[list[str], LineSpan, str]]:
    """
    Fallback regex-based parsing when bashlex fails.
    This is less accurate but handles more complex shell syntax.
    """
    import re
    import shlex
    
    results = []
    lines = text.split('\n')
    
    # Pattern to match pip install commands - more precise to avoid false positives
    pip_pattern = r'(?:^|[;&|]+\s*|&&\s*|\|\|\s*)(?:\w+\s+)*(?:sudo\s+)?(?:python\d*\s+-m\s+)?(?:uv\s+)?pip\d*\s+install\s+(?!install\s)[^;&|]*'
    
    for line_num, line in enumerate(lines, 1):
        # Handle line continuations by joining with next lines
        full_line = line
        current_line_num = line_num
        
        # Simple line continuation handling
        while full_line.rstrip().endswith('\\') and line_num < len(lines):
            line_num += 1
            if line_num <= len(lines):
                full_line = full_line.rstrip()[:-1] + ' ' + lines[line_num - 1].strip()
        
        # Find pip install commands in the line
        matches = re.finditer(pip_pattern, full_line, re.IGNORECASE)
        for match in matches:
            cmd_text = match.group(0).strip()
            # Clean up the command (remove leading separators)
            cmd_text = re.sub(r'^[;&|]+\s*|&&\s*|\|\|\s*', '', cmd_text).strip()
            
            try:
                # Try to split the command into words
                words = shlex.split(cmd_text)
            except Exception:
                # If shlex fails, do basic split
                words = cmd_text.split()
            
            if words:
                # Split the command text by pip install patterns to handle multiple commands
                # This handles cases like "python -m pip install pkg1 pip install pkg2"
                pip_commands = []
                remaining_text = cmd_text
                
                # Find all pip install command starts
                pip_install_pattern = r'(?:(?:python\d*\s+-m\s+)?(?:uv\s+)?pip\d*\s+install|pip\d*\s+install)'
                matches = list(re.finditer(pip_install_pattern, remaining_text, re.IGNORECASE))
                
                if len(matches) > 1:
                    # Multiple pip install commands found, split them
                    for i, match in enumerate(matches):
                        start = match.start()
                        end = matches[i + 1].start() if i + 1 < len(matches) else len(remaining_text)
                        single_cmd = remaining_text[start:end].strip()
                        if single_cmd:
                            try:
                                cmd_words = shlex.split(single_cmd)
                                pip_commands.append((cmd_words, single_cmd))
                            except Exception:
                                cmd_words = single_cmd.split()
                                pip_commands.append((cmd_words, single_cmd))
                else:
                    # Single command
                    pip_commands.append((words, cmd_text))
                
                # Add each pip command as a separate result
                for cmd_words, single_cmd_text in pip_commands:
                    if cmd_words:
                        results.append((cmd_words, (current_line_num, line_num), single_cmd_text))
    
    return results


def _basename(s: str) -> str:
    return os.path.basename(s)


def _looks_like_python(exe: str) -> bool:
    b = _basename(exe)
    if b == "python":
        return True
    if not b.startswith("python"):
        return False
    tail = b[len("python"):]
    return all(c.isdigit() or c == "." or c == "m" for c in tail)


def _looks_like_pip(exe: str) -> bool:
    b = _basename(exe)
    if b == "pip":
        return True
    if not b.startswith("pip"):
        return False
    tail = b[len("pip"):]
    return all(c.isdigit() or c == "." for c in tail)


# common wrappers; include "-" to absorb YAML bullets
_WRAPPERS = {"sudo", "env", "time", "nice", "stdbuf", "chrt", "nohup", "-"}

def _strip_wrappers(argv: list[str]) -> list[str]:
    i = 0
    # leading VAR=val
    while i < len(argv) and "=" in argv[i] and not argv[i].startswith("-"):
        i += 1
    # single wrapper layer
    if i < len(argv) and _basename(argv[i]) in _WRAPPERS:
        i += 1
        while i < len(argv) and argv[i].startswith("-"):
            # sudo -u USER
            if argv[i] in ("-u", "--user") and i + 1 < len(argv):
                i += 2
            else:
                i += 1
        while i < len(argv) and "=" in argv[i] and not argv[i].startswith("-"):
            i += 1
    return argv[i:]


def _extract_install_args(argv: list[str]) -> Optional[list[str]]:
    """
    Return sub-argv after 'install' for:
      - pip[<ver>] install ...
      - python -m pip install ...
      - uv pip install ...
    else None.
    """
    a = _strip_wrappers(argv)
    if not a:
        return None

    # uv pip install ...
    if _basename(a[0]) == "uv":
        if len(a) >= 3 and a[1] == "pip" and a[2] == "install":
            return a[3:]
        return None

    # python -m pip install ...
    if _looks_like_python(a[0]):
        for j in range(1, len(a) - 1):
            if a[j] == "-m" and j + 1 < len(a) and _basename(a[j + 1]) == "pip":
                k = j + 2
                if k < len(a) and a[k] == "install":
                    return a[k + 1:]
                return None

    # pip[ver] install ...
    if _looks_like_pip(a[0]):
        if len(a) >= 2 and a[1] == "install":
            return a[2:]

    return None


# ---- argv(after 'install') → requirement specs (options vs args) ----

_FLAGS_WITH_VALUE = {
    "-r", "--requirement",
    "-c", "--constraint",
    "-i", "--index-url",
    "--extra-index-url",
    "-f", "--find-links",
    "--trusted-host", "--proxy",
    "--src", "--target", "-t", "--root", "--prefix",
    "--global-option", "--install-option",
    "--hash", "--only-binary", "--no-binary",
    "--abi", "--platform", "--implementation", "--python",
    "--report", "--config-settings", "-C",
}
_EDITABLE_FLAGS = {"-e", "--editable"}

def _split_specs_with_pip_parser(args: list[str]) -> list[str]:
    if _PIP_INSTALL_PARSER is not None:
        try:
            buf = io.StringIO()
            err_buf = io.StringIO()
            import contextlib
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err_buf):
                _, specs = _PIP_INSTALL_PARSER.parse_args(args)
            return list(specs)
        except (SystemExit, Exception):
            pass  # fall through to conservative manual split

    specs: list[str] = []
    i = 0
    in_command_substitution = False
    
    while i < len(args):
        tok = args[i]

        if tok == "--":
            specs.extend(args[i + 1:])
            break

        # Track command substitutions that span multiple tokens
        if tok.startswith("$(") or tok.startswith("`") or tok.startswith("${"):
            in_command_substitution = True
        
        if in_command_substitution:
            # Skip everything until we find the end of the command substitution
            if tok.endswith(")") or tok.endswith("`") or tok.endswith("}"):
                in_command_substitution = False
            i += 1
            continue

        if tok in _EDITABLE_FLAGS:
            # skip editable arg (path/url) if present
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
            continue

        if tok.startswith("--") and "=" in tok:
            flag, _, _val = tok.partition("=")
            if flag in _FLAGS_WITH_VALUE:
                i += 1
                continue

        if tok.startswith("-"):
            if tok in _FLAGS_WITH_VALUE and i + 1 < len(args):
                i += 2
            else:
                i += 1
            continue

        # positional candidate requirement
        specs.append(tok)
        i += 1

    return specs


# ---- specs → canonical project names (PEP-508/503), drop paths/urls/files ----

# _ARCHIVE_EXTS = (
#     ".whl", ".zip", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar",
#     ".gz", ".bz2", ".xz", ".egg",
# )

# def _looks_like_file(s: string) -> bool:  # type: ignore[name-defined]
#     raise NotImplementedError  # Avoid accidental usage if someone copies partial code


_ARCHIVE_EXTS = (
    ".whl", ".zip", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar",
    ".gz", ".bz2", ".xz", ".egg",
)

def _looks_like_file(s: str) -> bool:
    low = s.lower()
    if any(low.endswith(ext) for ext in _ARCHIVE_EXTS):
        return True
    if low.endswith(".txt"):  # requirements-like
        return True
    if "://" in s:           # direct URL
        return True
    return False

def _looks_dynamic_or_path(s: str) -> bool:
    if any(x in s for x in ("$(", "${", "$", "`")):
        return True
    if s.startswith(("./", "../", "/")):
        return True
    # windows-ish path (best-effort)
    if re.match(r"^[A-Za-z]:\\", s):
        return True
    if os.sep in s or (os.altsep and os.altsep in s):
        return True
    return False

def _is_canonical_project_name(name: str) -> bool:
    # canonicalize_name -> [a-z0-9]+(?:-[a-z0-9]+)*
    # Filter out packages with invalid characters (only allow a-z, 0-9, -, _)
    if not name or name[0] == "-" or name[-1] == "-":
        return False
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False
    for c in name:
        if not (c.isdigit() or ("a" <= c <= "z") or c == "-"):
            return False
    return True

def _names_from_specs(specs: Iterable[str]) -> list[str]:
    names: set[str] = set()
    for spec in specs:
        if _looks_like_file(spec) or _looks_dynamic_or_path(spec):
            continue
        try:
            req = Requirement(spec)
        except Exception:
            continue
        if getattr(req, "url", None):
            continue  # direct reference (name @ url)
        canon = canonicalize_name(req.name)
        if _is_canonical_project_name(canon):
            names.add(canon)
    return sorted(names)


def extract_pip_installs_from_shell(text: str) -> list[DetectedCommand]:
    """
    Parse arbitrary shell text and return detected pip install commands with
    canonical project names and exact line spans/snippets.
    """
    results: list[DetectedCommand] = []
    for words, (sline, eline), snippet in _iter_shell_commands(text):
        # Convert bash words to argv (handles quotes/escapes)
        try:
            argv = shlex.split(" ".join(words), posix=True)
        except Exception:
            continue

        install_args = _extract_install_args(argv)
        if install_args is None:
            continue

        specs = _split_specs_with_pip_parser(install_args)
        pkgs = _names_from_specs(specs)
        if pkgs:
            results.append(DetectedCommand(
                packages=pkgs,
                line_numbers=(sline, eline),
                snippet=snippet.strip()
            ))
    return results


def _iter_dockerfile_runs(text: str):
    """
    Yield (run_text, start_line, end_line) for each RUN instruction.
    Supports shell form and exec JSON-array form (e.g. ["bash","-lc","..."]).
    """
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i]
        if not raw.lstrip().startswith("RUN"):
            i += 1
            continue

        start_line = i + 1
        body = raw.split("RUN", 1)[1].lstrip()

        # Shell form with backslashes
        if not body.startswith("["):
            j = i
            composed = body
            while composed.rstrip().endswith("\\") and j + 1 < n:
                j += 1
                composed = composed.rstrip()[:-1] + " " + lines[j].strip()
            end_line = j + 1
            yield composed, start_line, end_line
            i = j + 1
            continue

        # Exec (JSON) form
        buf = body
        j = i
        while buf.count("[") > buf.count("]") and j + 1 < n:
            j += 1
            buf += lines[j]
        end_line = j + 1
        try:
            arr = json.loads(buf)
            run_text = ""
            if isinstance(arr, list) and arr:
                if arr[0] in ("bash", "/bin/bash", "sh", "/bin/sh") and "-c" in arr:
                    k = arr.index("-c")
                    run_text = arr[k + 1] if k + 1 < len(arr) else ""
                else:
                    run_text = " ".join(arr)
            if run_text:
                yield run_text, start_line, end_line
        except Exception:
            pass
        i = j + 1


def extract_pip_installs_from_dockerfile(text: str) -> list[DetectedCommand]:
    out: list[DetectedCommand] = []
    for body, sline, eline in _iter_dockerfile_runs(text):
        sub = extract_pip_installs_from_shell(body)
        for dc in sub:
            # For Dockerfile RUN commands, use the actual Dockerfile line numbers
            # instead of the relative line numbers from shell parsing
            out.append(DetectedCommand(
                packages=dc.packages,
                line_numbers=(sline, eline),
                snippet=dc.snippet or body.strip()
            ))
    return out


# Keep your ABC if needed; here we only provide the concrete class.
@dataclass
class PIPParser:
    name: str = "pip"

    def get_packages(self, text: str, file_type: str = "script") -> List[DetectedCommand]:
        """
        Accepts text and returns DetectedCommand entries.
        Uses appropriate parsing method based on file_type.
        
        Args:
            text: The file content to parse
            file_type: The type of file ("dockerfile", "gitlab-ci", "script")
        """
        if file_type == "dockerfile":
            return extract_pip_installs_from_dockerfile(text)
        else:
            # For gitlab-ci and script files, use shell parsing
            return extract_pip_installs_from_shell(text)