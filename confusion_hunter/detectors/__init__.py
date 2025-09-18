import os
from .schema_loader import SchemaLoader

# Get the schemas directory path
_schemas_dir = os.path.join(os.path.dirname(__file__), 'schemas')

# Create schema-based detector instances
PythonDetector = SchemaLoader.create_detector(os.path.join(_schemas_dir, 'python_detector.json'))
JavaScriptDetector = SchemaLoader.create_detector(os.path.join(_schemas_dir, 'javascript_detector.json'))
MavenDetector = SchemaLoader.create_detector(os.path.join(_schemas_dir, 'maven_detector.json'))
GradleDetector = MavenDetector  # Gradle uses the same schema as Maven for now

# Additional detectors from schemas
PipInstallDetector = SchemaLoader.create_detector(os.path.join(_schemas_dir, 'pip_install_detector.json'))
NPMInstallDetector = SchemaLoader.create_detector(os.path.join(_schemas_dir, 'npm_install_detector.json'))