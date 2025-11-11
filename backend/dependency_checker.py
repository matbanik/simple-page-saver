"""
Dependency Checker for Simple Page Saver
Validates that all required libraries are installed with correct versions
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional


class DependencyChecker:
    """Checks if all required dependencies are installed with correct versions"""

    def __init__(self, requirements_file: str = "requirements.txt"):
        """
        Initialize the dependency checker

        Args:
            requirements_file: Path to requirements.txt file
        """
        self.requirements_file = Path(__file__).parent / requirements_file
        self.missing_packages: List[str] = []
        self.version_mismatches: List[Tuple[str, str, str]] = []
        self.import_errors: Dict[str, str] = {}

    def parse_requirement(self, line: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse a requirement line from requirements.txt

        Args:
            line: A line from requirements.txt

        Returns:
            Tuple of (package_name, operator, version) or None if invalid
        """
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            return None

        # Handle package[extra]>=version format
        match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_,]+\])?)\s*(>=|==|<=|>|<|!=)\s*(.+)$', line)
        if match:
            package_name = match.group(1)
            operator = match.group(2)
            version = match.group(3).strip()

            # Remove [extra] from package name for import checking
            package_base = re.sub(r'\[.*\]', '', package_name)

            return (package_base, operator, version)

        return None

    def get_package_version(self, package_name: str) -> Optional[str]:
        """
        Get the installed version of a package

        Args:
            package_name: Name of the package

        Returns:
            Version string or None if not installed
        """
        try:
            # Try using importlib.metadata (Python 3.8+)
            from importlib.metadata import version
            return version(package_name)
        except ImportError:
            # Fallback for older Python versions
            try:
                import pkg_resources
                return pkg_resources.get_distribution(package_name).version
            except Exception:
                return None
        except Exception:
            return None

    def compare_versions(self, installed: str, required: str, operator: str) -> bool:
        """
        Compare version strings

        Args:
            installed: Installed version string
            required: Required version string
            operator: Comparison operator (>=, ==, <=, >, <, !=)

        Returns:
            True if version comparison passes, False otherwise
        """
        try:
            from packaging import version as pkg_version
            installed_v = pkg_version.parse(installed)
            required_v = pkg_version.parse(required)

            if operator == '>=':
                return installed_v >= required_v
            elif operator == '==':
                return installed_v == required_v
            elif operator == '<=':
                return installed_v <= required_v
            elif operator == '>':
                return installed_v > required_v
            elif operator == '<':
                return installed_v < required_v
            elif operator == '!=':
                return installed_v != required_v
            else:
                return True
        except ImportError:
            # If packaging module not available, do simple string comparison
            if operator == '>=':
                return installed >= required
            elif operator == '==':
                return installed == required
            else:
                return True
        except Exception:
            # If comparison fails, assume it's OK
            return True

    def check_dependencies(self) -> bool:
        """
        Check all dependencies from requirements.txt

        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        if not self.requirements_file.exists():
            print(f"Warning: Requirements file not found: {self.requirements_file}")
            return True  # Continue without checking

        self.missing_packages = []
        self.version_mismatches = []
        self.import_errors = {}

        with open(self.requirements_file, 'r') as f:
            for line in f:
                parsed = self.parse_requirement(line)
                if not parsed:
                    continue

                package_name, operator, required_version = parsed

                # Get installed version
                installed_version = self.get_package_version(package_name)

                if installed_version is None:
                    self.missing_packages.append(f"{package_name}{operator}{required_version}")
                else:
                    # Check version compatibility
                    if not self.compare_versions(installed_version, required_version, operator):
                        self.version_mismatches.append((
                            package_name,
                            installed_version,
                            f"{operator}{required_version}"
                        ))

        return len(self.missing_packages) == 0 and len(self.version_mismatches) == 0

    def print_report(self) -> None:
        """Print a detailed report of dependency issues"""
        if self.missing_packages:
            print("\n" + "=" * 70)
            print("ERROR: Missing Required Libraries")
            print("=" * 70)
            print("\nThe following packages are not installed:\n")
            for package in self.missing_packages:
                print(f"  ✗ {package}")
            print("\nTo install missing packages, run:")
            print(f"  pip install -r {self.requirements_file.name}")
            print("=" * 70 + "\n")

        if self.version_mismatches:
            print("\n" + "=" * 70)
            print("ERROR: Version Mismatches")
            print("=" * 70)
            print("\nThe following packages have incompatible versions:\n")
            for package, installed, required in self.version_mismatches:
                print(f"  ✗ {package}")
                print(f"    Installed: {installed}")
                print(f"    Required:  {required}")
            print("\nTo upgrade packages, run:")
            print(f"  pip install --upgrade -r {self.requirements_file.name}")
            print("=" * 70 + "\n")

        if self.import_errors:
            print("\n" + "=" * 70)
            print("ERROR: Import Failures")
            print("=" * 70)
            print("\nThe following packages could not be imported:\n")
            for package, error in self.import_errors.items():
                print(f"  ✗ {package}: {error}")
            print("=" * 70 + "\n")


def check_dependencies_at_startup() -> bool:
    """
    Convenience function to check dependencies at application startup

    Returns:
        True if all dependencies are satisfied, False otherwise
    """
    checker = DependencyChecker()

    print("Checking required libraries...")

    if checker.check_dependencies():
        print("✓ All required libraries are installed\n")
        return True
    else:
        checker.print_report()
        return False


if __name__ == "__main__":
    """Run dependency check standalone"""
    if not check_dependencies_at_startup():
        sys.exit(1)
    else:
        print("Dependency check passed!")
