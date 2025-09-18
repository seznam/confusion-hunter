import re
from typing import List, Dict, Any, Optional

class BuildGradleParser:
    """Parser for Gradle build.gradle and build.gradle.kts files"""
    
    # Regular expressions for matching different dependency formats in build.gradle (Groovy DSL)
    IMPLEMENTATION_PATTERN = re.compile(r'(?:implementation|api|compile|runtime|testImplementation|testCompile|testRuntime|compileOnly|runtimeOnly|annotationProcessor)\s+[\'"](.*?):([^:]+?)(?::.*?)?[\'"]')
    
    # Regular expressions for matching Kotlin DSL dependency formats in build.gradle.kts
    KTS_IMPLEMENTATION_PATTERN = re.compile(r'(?:implementation|api|compile|runtime|testImplementation|testCompile|testRuntime|compileOnly|runtimeOnly|annotationProcessor)\([\'"](.*?):([^:]+?)(?::.*?)?[\'"]')
    
    # Pattern to match variable definitions in Groovy DSL
    EXT_BLOCK_PATTERN = re.compile(r'ext\s*\{(.*?)\}', re.DOTALL)
    VARIABLE_DEFINITION_PATTERN = re.compile(r'(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]')
    
    # Pattern to match variable definitions in Kotlin DSL
    KTS_VARIABLE_PATTERN = re.compile(r'val\s+(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]')
    
    # Pattern for groovy with parentheses implementation("group:artifact:version")
    IMPLEMENTATION_PARENTHESES_PATTERN = re.compile(r'(?:implementation|api|compile|runtime|testImplementation|testCompile|testRuntime|compileOnly|runtimeOnly|annotationProcessor)\s*\([\'"](.*?):([^:]+?)(?::.*?)?[\'"]')
    
    @staticmethod
    def get_packages(file_path: str) -> List[Dict[str, str]]:
        """
        Parse build.gradle or build.gradle.kts file and extract package dependencies.
        Standard method name for consistent interface across parsers.
        
        Args:
            file_path (str): Path to the build.gradle file
            
        Returns:
            List[Dict[str, str]]: List of Maven artifacts with groupId and artifactId
        """
        return BuildGradleParser.parse_gradle_file(file_path)
    
    @staticmethod
    def _extract_variables(content: str, is_kts: bool = False) -> Dict[str, str]:
        """
        Extract variable definitions from the Gradle file
        
        Args:
            content (str): Content of the build.gradle file
            is_kts (bool): Whether this is a Kotlin DSL file
            
        Returns:
            Dict[str, str]: Dictionary of variable names and their values
        """
        variables = {}
        
        if is_kts:
            # Extract Kotlin DSL variables (val declarations)
            for var_match in BuildGradleParser.KTS_VARIABLE_PATTERN.finditer(content):
                var_name, var_value = var_match.groups()
                variables[var_name] = var_value
        else:
            # Find the ext block for Groovy DSL
            ext_match = BuildGradleParser.EXT_BLOCK_PATTERN.search(content)
            if ext_match:
                ext_block = ext_match.group(1)
                
                # Find variable definitions in the ext block
                for var_match in BuildGradleParser.VARIABLE_DEFINITION_PATTERN.finditer(ext_block):
                    var_name, var_value = var_match.groups()
                    variables[var_name] = var_value
        
        return variables
    
    @staticmethod
    def _resolve_artifact_id(artifact_id: str, variables: Dict[str, str]) -> str:
        """
        Resolve variables in artifact ID
        
        Args:
            artifact_id (str): Artifact ID with potential variables
            variables (Dict[str, str]): Dictionary of variable names and values
            
        Returns:
            str: Resolved artifact ID with variables replaced by their values
        """
        # Handle common patterns for Scala versions
        # e.g., spark-sql_$scalaVersion -> spark-sql_2.12
        for var_name, var_value in variables.items():
            # Replace ${varName} format
            artifact_id = artifact_id.replace(f"${{{var_name}}}", var_value)
            # Replace $varName format
            artifact_id = artifact_id.replace(f"${var_name}", var_value)
        
        return artifact_id
    
    @staticmethod
    def parse_gradle_file(file_path: str) -> List[Dict[str, str]]:
        """
        Parse build.gradle or build.gradle.kts file and extract Maven dependencies
        
        Args:
            file_path (str): Path to the build.gradle file
            
        Returns:
            List[Dict[str, str]]: List of Maven artifacts with groupId and artifactId
        """
        packages = []
        dependencies_section = False
        dependency_block_level = 0
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Determine if this is a Kotlin DSL file
            is_kts = file_path.endswith(".kts")
            
            # Extract variables from ext block or val declarations
            variables = BuildGradleParser._extract_variables(content, is_kts)
            
            # Find all implementation/api/compile style dependencies
            # Use appropriate pattern based on file type
            if is_kts:
                pattern = BuildGradleParser.KTS_IMPLEMENTATION_PATTERN
            else:
                pattern = BuildGradleParser.IMPLEMENTATION_PATTERN
                
            for match in pattern.finditer(content):
                group_id, artifact_id = match.groups()
                # Store both original and resolved versions
                raw_artifact_id = artifact_id
                resolved_artifact_id = BuildGradleParser._resolve_artifact_id(artifact_id, variables)
                
                packages.append({
                    'groupId': group_id,
                    'artifactId': resolved_artifact_id,
                    'rawArtifactId': raw_artifact_id
                })
            
            # For Groovy DSL, also check for implementation with parentheses
            if not is_kts:
                for match in BuildGradleParser.IMPLEMENTATION_PARENTHESES_PATTERN.finditer(content):
                    group_id, artifact_id = match.groups()
                    # Store both original and resolved versions
                    raw_artifact_id = artifact_id
                    resolved_artifact_id = BuildGradleParser._resolve_artifact_id(artifact_id, variables)
                    
                    packages.append({
                        'groupId': group_id,
                        'artifactId': resolved_artifact_id,
                        'rawArtifactId': raw_artifact_id
                    })
            
            # Parse line by line to handle multiline blocks
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip lines that are clearly not dependencies (URLs, etc.)
                if 'url ' in line or 'http' in line or 'image.set(' in line:
                    continue
                
                # Track when we enter the dependencies block
                if 'dependencies' in line and '{' in line:
                    dependencies_section = True
                    dependency_block_level = 1
                    continue
                
                # Track nested braces
                if dependencies_section:
                    dependency_block_level += line.count('{')
                    dependency_block_level -= line.count('}')
                    
                    # Exit dependencies section when block ends
                    if dependency_block_level <= 0:
                        dependencies_section = False
                        continue
                    
                    # Try to find dependencies in Kotlin DSL not captured by the regex
                    if is_kts and "(" in line and ")" in line and ":" in line:
                        # Look for patterns like 'implementation("org.apache.flink:flink-streaming-scala_${scalaVersion}:$flinkVersion")'
                        kts_match = re.search(r'[^(]+\([\'"]([^\'":]+):([^\'":]+)(?::.*?)?[\'"]', line)
                        if kts_match:
                            group_id, raw_artifact_id = kts_match.groups()
                            resolved_artifact_id = BuildGradleParser._resolve_artifact_id(raw_artifact_id, variables)
                            
                            packages.append({
                                'groupId': group_id,
                                'artifactId': resolved_artifact_id,
                                'rawArtifactId': raw_artifact_id
                            })
                    
                    # Try to find dependencies in Groovy DSL formats not captured by the regex
                    elif not is_kts:
                        # Try to find dependencies with group: and name: syntax
                        if 'group:' in line and 'name:' in line:
                            group_match = re.search(r'group:\s*[\'"](.+?)[\'"]', line)
                            name_match = re.search(r'name:\s*[\'"](.+?)[\'"]', line)
                            
                            if group_match and name_match:
                                group_id = group_match.group(1)
                                raw_artifact_id = name_match.group(1)
                                resolved_artifact_id = BuildGradleParser._resolve_artifact_id(raw_artifact_id, variables)
                                
                                packages.append({
                                    'groupId': group_id,
                                    'artifactId': resolved_artifact_id,
                                    'rawArtifactId': raw_artifact_id
                                })
                        
                        # Handle variable strings in coordinates with GString interpolation
                        elif not any(pattern in line for pattern in ['group:', 'name:']) and ':' in line:
                            # Look for patterns like 'org.apache.spark:spark-sql_$scalaVersion'
                            variable_match = re.search(r'[\'"]([^\'":]+):([^\'":]+)(?::.*?)?[\'"]', line)
                            if variable_match:
                                group_id, raw_artifact_id = variable_match.groups()
                                resolved_artifact_id = BuildGradleParser._resolve_artifact_id(raw_artifact_id, variables)
                                
                                packages.append({
                                    'groupId': group_id,
                                    'artifactId': resolved_artifact_id,
                                    'rawArtifactId': raw_artifact_id
                                })
            
        except Exception as e:
            print(f"Error reading Gradle file at {file_path}: {type(e).__name__}: {str(e)}")
        
        return packages