import re
import shlex
from typing import Tuple
from .base import DetectedCommand, PackageParser

class NPMParser(PackageParser):
    name = "npm"


    NPM_ALIASES = [
        "npm install",
        "npm i",
        "npm in",
        "npm ins",
        "npm inst",
        "npm insta",
        "npm instal",
        "npm isnt",
        "npm isnta",
        "npm isntal",
        "npm add",
    ]

    # regexes

    def _extract_all_commands(self, lines: str) -> list[str]:
        """
        Extract all commands from lines.
        """
        # 1. Remove backslash-newlines (line continuations)
        normalized = re.sub(r'\\\s*\n\s*', ' ', lines)

        # 2. Split into commands by `;`, `&&`, `||` or newlines boundaries that are NOT escaped
        # These separators are captured and preserved
        commands = re.split(r'\s*(?:;|&&|\|\||\n)\s*', normalized.strip())

        # 3. Filter out empty commands
        commands = [cmd.strip() for cmd in commands if cmd.strip()]

        return commands
    
    def _extract_npm_commands(self, lines: list[str]) -> list[str]:
        """
        Extract npm commands from lines.
        It finds the whole command like: [ "npm install ..." , "npm i ... ].
        It counts with the aliases and multiline commands.
        """
        # filter out anything that is not a npm command
        commands = [cmd for cmd in lines if any(alias in cmd for alias in self.NPM_ALIASES)]

        # remove all backslashes
        commands = [re.sub(r'\\', '', cmd).strip() for cmd in commands]

        return commands

    def _remove_version(self, arg: str) -> str:
        """
        Remove version from package name.
        """
        if arg.startswith("@"):
            # Handle scoped packages like @scope/package or @scope/package@1.2.3
            match = re.match(r"(@[^/]+/[^@]+)(?:@.*)?", arg)
            return match.group(1) if match else arg
        else:
            # Unscoped package, strip @version if present
            return arg.split("@")[0]


    def _extract_git_package(self, arg: str) -> str:
        """
        Extract git package from url.
        """
        # we want to extract name "repo" from 'git+https://github.com/user/repo.git'
        return arg.split("git+")[1].split("/")[-1].split(".")[0]
    
    def _extract_url_package(self, arg: str) -> str:
        """
        Extract package from url.
        """
        return arg.split("://")[1].split("/")[-1].split(".")[0]
    
    def _extract_npm_package(self, arg: str) -> str:
        """
        Extract package name from npm alias format like 'npm:package@version'.
        """
        # Remove 'npm:' prefix
        npm_spec = arg[4:]  # Remove 'npm:' prefix
        
        if npm_spec.startswith('@'):
            # Scoped package: @scope/package@version -> @scope/package
            parts = npm_spec.split('@')
            if len(parts) >= 3:  # @, scope/package, version
                return f"@{parts[1]}"
            else:
                return npm_spec.split('@')[0] if '@' in npm_spec[1:] else npm_spec
        else:
            # Regular package: package@version -> package
            return npm_spec.split('@')[0]
    
    def _filter_packages(self, args: list[str]) -> list[str]:
        """
        Get only packages from command. 
        Remove flags, version numbers, remove tar balls
        In case of urls we extract the package name from the url
        """
        pkgs = []
        for arg in args:

            if arg.endswith(">>") or arg.endswith(">") or arg.endswith("|") or arg.endswith("&"):
                # we ended the arguments with a redirect or pipe or ampersand, so we need dont continue
                break

            if arg.startswith("$"):
                continue # ignore environment variables

            if arg.startswith("--"):
                continue
            
            if arg.startswith("-"):
                continue
            
            if arg.startswith("git+"):
                arg = self._extract_git_package(arg)
            
            if "./" in arg or arg.startswith("/") or arg.endswith(".tgz"):
                continue # we ignore local packages
            
            # Filter out GitHub repository references (user/repo#tag format)
            # These are not relevant for dependency confusion as they're not from npm registry
            if "/" in arg and "#" in arg:
                continue # ignore GitHub repository references like "user/repo#tag"
            
            # Filter out other Git repository references
            if "/" in arg and not arg.startswith("@"):
                # This catches GitHub shorthand like "user/repo" but preserves scoped packages like "@scope/package"
                continue
            
            if "://" in arg:
                arg = self._extract_url_package(arg)
            
            elif arg.startswith("npm:"):
                arg = self._extract_npm_package(arg)

            # internal-package-69@1.0.0 -> internal-package-69
            # but @scope/internal-package-69@1.0.0 -> @scope/internal-package-69
            elif "@" in arg:
                arg = self._remove_version(arg)
            
            # Clean up quotes that might be left from shell parsing
            arg = arg.strip('\'"')

            # Filter out packages with invalid characters for npm (only allow a-z, A-Z, 0-9, -, _, @, /)
            if not re.match(r'^[@a-zA-Z0-9_/-]+$', arg):
                continue

            pkgs.append(arg)

        return pkgs

    def _extract_arguments(self, cmd: str) -> list[str]:
            """
            Extracts the arguments passed to an 'npm install' command.

            Handles common patterns such as:
            - "npm install foo"
            - "RUN npm i bar"
            - "- npm install baz"

            Returns:
                A list of package names passed to the install command, or an empty list if not found.
            """
            try:
                parts = shlex.split(cmd)
            except Exception as e:
                return []

            for i in range(len(parts) - 1):
                if parts[i] == "npm":
                    next_part = parts[i + 1]
                    full_cmd = f"npm {next_part}"
                    if full_cmd in self.NPM_ALIASES:
                        return parts[i + 2:]
            return []


    def get_packages(self, text: str, file_type: str = "script") -> list[DetectedCommand]:
        """
        Main entry point: extract all npm install package names from text.
        Uses appropriate parsing method based on file_type.
        
        Args:
            text: The file content to parse
            file_type: The type of file ("dockerfile", "gitlab-ci", "script")
        """
        if file_type == "gitlab-ci":
            return self._extract_npm_installs_from_gitlab_ci(text)
        else:
            # For dockerfile and script files, use shell parsing
            return self._extract_npm_installs_with_line_numbers(text)

    def _extract_npm_installs_from_gitlab_ci(self, text: str) -> list[DetectedCommand]:
        """
        Extract npm install commands from GitLab CI YAML files.
        """
        import re
        import shlex
        
        results = []
        lines = text.split('\n')
        
        # Pattern to match YAML list items with npm install commands
        npm_pattern = r'^\s*-\s+npm\s+(?:install|i|in|ins|inst|insta|instal|isnt|isnta|isntal|add)\b.*'
        
        for line_num, line in enumerate(lines, 1):
            if re.match(npm_pattern, line, re.IGNORECASE):
                # Extract the command part after the YAML list marker
                cmd_text = re.sub(r'^\s*-\s+', '', line).strip()
                
                if cmd_text.strip().startswith("#"):
                    continue  # ignore commented command lines
                
                try:
                    # Try to split the command into words
                    words = shlex.split(cmd_text)
                except Exception:
                    # If shlex fails, do basic split
                    words = cmd_text.split()
                
                if words:
                    args = self._extract_arguments_from_words(words)
                    pkgs = self._filter_packages(args)
                    if pkgs:
                        results.append(DetectedCommand(
                            packages=pkgs, 
                            line_numbers=(line_num, line_num), 
                            snippet=cmd_text
                        ))
        
        return results

    def _extract_npm_installs_with_line_numbers(self, text: str) -> list[DetectedCommand]:
        """
        Extract npm install commands with proper line numbers and snippets.
        """
        import re
        import shlex
        
        results = []
        lines = text.split('\n')
        
        # Pattern to match npm install commands
        npm_pattern = r'(?:^|[;&|]+\s*|&&\s*|\|\|\s*)(?:\w+\s+)*npm\s+(?:install|i|in|ins|inst|insta|instal|isnt|isnta|isntal|add)\b[^;&|]*'
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_num = i + 1
            
            # Handle line continuations by joining with next lines
            full_line = line
            current_line_num = line_num
            end_line_num = line_num
            
            # Simple line continuation handling
            while full_line.rstrip().endswith('\\') and end_line_num < len(lines):
                end_line_num += 1
                if end_line_num <= len(lines):
                    full_line = full_line.rstrip()[:-1] + ' ' + lines[end_line_num - 1].strip()
            
            # Skip ahead if we processed multiple lines
            if end_line_num > line_num:
                i = end_line_num
            else:
                i += 1
            
            # Find npm install commands in the line
            matches = re.finditer(npm_pattern, full_line, re.IGNORECASE)
            for match in matches:
                cmd_text = match.group(0).strip()
                # Clean up the command (remove leading separators)
                cmd_text = re.sub(r'^[;&|]+\s*|&&\s*|\|\|\s*', '', cmd_text).strip()
                
                if cmd_text.strip().startswith("#"):
                    continue  # ignore commented command lines
                
                try:
                    # Try to split the command into words
                    words = shlex.split(cmd_text)
                except Exception:
                    # If shlex fails, do basic split
                    words = cmd_text.split()
                
                if words:
                    args = self._extract_arguments_from_words(words)
                    pkgs = self._filter_packages(args)
                    if pkgs:
                        results.append(DetectedCommand(
                            packages=pkgs, 
                            line_numbers=(current_line_num, end_line_num), 
                            snippet=cmd_text
                        ))
        
        return results

    def _extract_arguments_from_words(self, words: list[str]) -> list[str]:
        """
        Extract arguments from already split words.
        """
        for i in range(len(words) - 1):
            if words[i] == "npm":
                next_part = words[i + 1]
                full_cmd = f"npm {next_part}"
                if full_cmd in self.NPM_ALIASES:
                    return words[i + 2:]
        return []