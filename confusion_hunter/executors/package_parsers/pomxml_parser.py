import xml.etree.ElementTree as ET
from typing import List, Dict, Any
import re

class PomXmlParser:
    """Parser for Maven pom.xml files"""
    
    # XML namespace mapping for Maven POM files
    NAMESPACES = {
        'maven': 'http://maven.apache.org/POM/4.0.0'
    }
    
    @staticmethod
    def get_packages(file_path: str) -> List[Dict[str, str]]:
        """
        Parse pom.xml file and extract package dependencies.
        Standard method name for consistent interface across parsers.
        
        Args:
            file_path (str): Path to the pom.xml file
            
        Returns:
            List[Dict[str, str]]: List of Maven artifacts with groupId and artifactId
        """
        return PomXmlParser.parse_pom_file(file_path)
    
    @staticmethod
    def parse_pom_file(file_path: str) -> List[Dict[str, str]]:
        """
        Parse pom.xml file and extract Maven dependencies
        
        Args:
            file_path (str): Path to the pom.xml file
            
        Returns:
            List[Dict[str, str]]: List of Maven artifacts with groupId and artifactId
        """
        packages = []
        properties = {}
        
        try:
            # Parse the XML file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Handle namespace in Maven POM files
            if root.tag.startswith('{'):
                # Extract namespace from root tag
                ns = re.match(r'\{(.*?)\}', root.tag).group(1)
                # Update namespaces dict with the actual namespace
                namespaces = {'maven': ns}
            else:
                namespaces = PomXmlParser.NAMESPACES
            
            # Extract properties first for variable substitution
            props_section = PomXmlParser._find_all_elements(root, './/maven:properties', namespaces)
            for props in props_section:
                for prop in props:
                    # Strip namespace from tag name if present
                    tag = prop.tag
                    if tag.startswith('{'):
                        tag = tag.split('}', 1)[1]
                    properties[tag] = prop.text.strip() if prop.text else ""
            
            # Extract dependencies from <dependencies> section
            dependencies_sections = PomXmlParser._find_all_elements(root, './/maven:dependencies', namespaces)
            
            for dependencies in dependencies_sections:
                for dependency in PomXmlParser._find_all_elements(dependencies, './maven:dependency', namespaces):
                    group_id = PomXmlParser._get_element_text(dependency, './maven:groupId', namespaces)
                    artifact_id = PomXmlParser._get_element_text(dependency, './maven:artifactId', namespaces)
                    
                    # Resolve properties in groupId and artifactId
                    group_id = PomXmlParser._resolve_properties(group_id, properties)
                    artifact_id = PomXmlParser._resolve_properties(artifact_id, properties)
                    
                    if group_id and artifact_id:
                        packages.append({
                            'groupId': group_id,
                            'artifactId': artifact_id
                        })
            
            # Extract dependencies from dependencyManagement section
            dep_mgmt_sections = PomXmlParser._find_all_elements(root, './/maven:dependencyManagement/maven:dependencies', namespaces)
            
            for dependencies in dep_mgmt_sections:
                for dependency in PomXmlParser._find_all_elements(dependencies, './maven:dependency', namespaces):
                    group_id = PomXmlParser._get_element_text(dependency, './maven:groupId', namespaces)
                    artifact_id = PomXmlParser._get_element_text(dependency, './maven:artifactId', namespaces)
                    
                    # Resolve properties in groupId and artifactId
                    group_id = PomXmlParser._resolve_properties(group_id, properties)
                    artifact_id = PomXmlParser._resolve_properties(artifact_id, properties)
                    
                    if group_id and artifact_id:
                        packages.append({
                            'groupId': group_id,
                            'artifactId': artifact_id
                        })
            
        except Exception as e:
            print(f"Error reading pom.xml file at {file_path}: {str(e)}")
        
        return packages
    
    @staticmethod
    def _resolve_properties(value: str, properties: Dict[str, str]) -> str:
        """
        Resolve Maven property references in a string
        
        Args:
            value (str): The string potentially containing property references
            properties (Dict[str, str]): Dictionary of property names and values
            
        Returns:
            str: The string with property references resolved
        """
        if not value or not properties:
            return value
            
        # Find all property references of the form ${property.name}
        property_refs = re.findall(r'\$\{([^}]+)\}', value)
        
        # Replace each property reference with its value
        result = value
        for prop_name in property_refs:
            if prop_name in properties:
                result = result.replace(f"${{{prop_name}}}", properties[prop_name])
                
        return result
    
    @staticmethod
    def _find_all_elements(element: ET.Element, xpath: str, namespaces: Dict[str, str]) -> List[ET.Element]:
        """Helper method to find all elements matching an XPath with namespaces"""
        try:
            return element.findall(xpath, namespaces)
        except Exception:
            # Fallback to searching without namespaces if there's an issue
            clean_xpath = xpath.replace('maven:', '')
            return element.findall(clean_xpath)
    
    @staticmethod
    def _get_element_text(element: ET.Element, xpath: str, namespaces: Dict[str, str]) -> str:
        """Helper method to get element text with namespace handling"""
        try:
            el = element.find(xpath, namespaces)
            return el.text.strip() if el is not None and el.text else ""
        except Exception:
            # Fallback to searching without namespaces if there's an issue
            clean_xpath = xpath.replace('maven:', '')
            el = element.find(clean_xpath)
            return el.text.strip() if el is not None and el.text else ""