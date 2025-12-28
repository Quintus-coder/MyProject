"""
JSON Comparator - A utility for comparing two JSON files.

This module provides functionality to compare two JSON files and identify
differences between them, including added, removed, and modified fields.
"""

import json
import sys
from typing import Any, Dict, List, Tuple
from pathlib import Path


class JSONComparator:
    """A class for comparing two JSON files and reporting differences."""

    def __init__(self, file1_path: str, file2_path: str):
        """
        Initialize the JSONComparator with two file paths.

        Args:
            file1_path: Path to the first JSON file.
            file2_path: Path to the second JSON file.
        """
        self.file1_path = file1_path
        self.file2_path = file2_path
        self.data1 = None
        self.data2 = None
        self.differences = {
            'added': [],
            'removed': [],
            'modified': [],
            'equal': True
        }

    def load_files(self) -> bool:
        """
        Load and parse both JSON files.

        Returns:
            bool: True if both files were loaded successfully, False otherwise.
        """
        try:
            with open(self.file1_path, 'r', encoding='utf-8') as f:
                self.data1 = json.load(f)
            print(f"✓ Loaded: {self.file1_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"✗ Error loading {self.file1_path}: {e}")
            return False

        try:
            with open(self.file2_path, 'r', encoding='utf-8') as f:
                self.data2 = json.load(f)
            print(f"✓ Loaded: {self.file2_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"✗ Error loading {self.file2_path}: {e}")
            return False

        return True

    def compare(self) -> Dict[str, Any]:
        """
        Compare the two JSON files.

        Returns:
            dict: A dictionary containing the comparison results.
        """
        if self.data1 is None or self.data2 is None:
            print("Error: Files not loaded. Call load_files() first.")
            return self.differences

        if self.data1 == self.data2:
            self.differences['equal'] = True
            return self.differences

        self.differences['equal'] = False
        self._compare_dicts(self.data1, self.data2)
        return self.differences

    def _compare_dicts(self, dict1: Dict, dict2: Dict, path: str = "") -> None:
        """
        Recursively compare two dictionaries.

        Args:
            dict1: First dictionary.
            dict2: Second dictionary.
            path: Current path in the nested structure.
        """
        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            return

        # Check for added and modified keys
        for key, value1 in dict1.items():
            current_path = f"{path}.{key}" if path else key
            if key not in dict2:
                self.differences['removed'].append(current_path)
            elif isinstance(value1, dict) and isinstance(dict2[key], dict):
                self._compare_dicts(value1, dict2[key], current_path)
            elif value1 != dict2[key]:
                self.differences['modified'].append({
                    'path': current_path,
                    'old_value': value1,
                    'new_value': dict2[key]
                })

        # Check for added keys
        for key, value2 in dict2.items():
            current_path = f"{path}.{key}" if path else key
            if key not in dict1:
                self.differences['added'].append(current_path)

    def print_report(self) -> None:
        """Print a formatted comparison report."""
        print("\n" + "=" * 60)
        print("JSON COMPARISON REPORT")
        print("=" * 60)

        if self.differences['equal']:
            print("\n✓ The JSON files are identical.")
            return

        print(f"\nFile 1: {self.file1_path}")
        print(f"File 2: {self.file2_path}\n")

        if self.differences['added']:
            print("ADDED FIELDS (in File 2):")
            for field in self.differences['added']:
                print(f"  + {field}")

        if self.differences['removed']:
            print("\nREMOVED FIELDS (from File 1):")
            for field in self.differences['removed']:
                print(f"  - {field}")

        if self.differences['modified']:
            print("\nMODIFIED FIELDS:")
            for mod in self.differences['modified']:
                print(f"  ~ {mod['path']}")
                print(f"    Old: {mod['old_value']}")
                print(f"    New: {mod['new_value']}")

        print("\n" + "=" * 60)

    def save_report(self, output_path: str) -> bool:
        """
        Save the comparison report to a JSON file.

        Args:
            output_path: Path where to save the report.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.differences, f, indent=2)
            print(f"✓ Report saved to: {output_path}")
            return True
        except Exception as e:
            print(f"✗ Error saving report: {e}")
            return False


def main():
    """Main entry point for the JSON comparator."""
    if len(sys.argv) < 3:
        print("Usage: python json_comparator.py <file1> <file2> [output_report]")
        print("Example: python json_comparator.py data1.json data2.json report.json")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    output_report = sys.argv[3] if len(sys.argv) > 3 else None

    comparator = JSONComparator(file1, file2)

    if not comparator.load_files():
        sys.exit(1)

    comparator.compare()
    comparator.print_report()

    if output_report:
        comparator.save_report(output_report)


if __name__ == "__main__":
    main()
