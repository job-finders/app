#!/usr/bin/env python3
"""
Documentation Validation Tool for Job Finders Platform

This tool validates route documentation for completeness, consistency, and accuracy.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import yaml


class DocumentationValidator:
    """Validates route documentation files for completeness and consistency."""

    def __init__(self, docs_dir: str = "src/routes/documentation"):
        self.docs_dir = Path(docs_dir)
        self.validation_results = {
            'errors': [],
            'warnings': [],
            'info': [],
            'stats': {}
        }

        # Required sections for route documentation
        self.required_sections = [
            'Overview',
            'Routes',
            'Metadata',
            'Description',
            'Workflow Integration',
            'Parameters',
            'Responses',
            'Security Considerations',
            'Examples'
        ]

        # Optional sections
        self.optional_sections = [
            'Template Context',
            'Controller Integration',
            'Related Routes',
            'Notes'
        ]

    def validate_all_documentation(self) -> Dict[str, Any]:
        """Validate all documentation files."""
        self.validation_results = {
            'errors': [],
            'warnings': [],
            'info': [],
            'stats': {}
        }

        # Find all documentation files
        doc_files = self._find_documentation_files()

        # Validate each file
        for doc_file in doc_files:
            self._validate_documentation_file(doc_file)

        # Generate statistics
        self._generate_statistics(doc_files)

        return self.validation_results

    def _find_documentation_files(self) -> List[Path]:
        """Find all markdown documentation files."""
        doc_files = []

        for root, dirs, files in os.walk(self.docs_dir):
            # Skip tools directory
            dirs[:] = [d for d in dirs if d != 'tools']

            for file in files:
                if file.endswith('.md') and not file.startswith('_') and file != 'README.md':
                    doc_files.append(Path(root) / file)

        return doc_files

    def _validate_documentation_file(self, doc_file: Path):
        """Validate a single documentation file."""
        try:
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Basic file validation
            self._validate_file_structure(doc_file, content)

            # Content validation
            self._validate_content_sections(doc_file, content)

            # Format validation
            self._validate_markdown_format(doc_file, content)

            # Cross-reference validation
            self._validate_cross_references(doc_file, content)

        except Exception as e:
            self._add_error(doc_file, f"Failed to validate file: {e}")

    def _validate_file_structure(self, doc_file: Path, content: str):
        """Validate basic file structure."""
        if not content.strip():
            self._add_error(doc_file, "File is empty")
            return

        # Check for main heading
        if not content.startswith('#'):
            self._add_error(doc_file, "File should start with a main heading (#)")

        # Check for overview section
        if '## Overview' not in content:
            self._add_error(doc_file, "Missing required 'Overview' section")

        # Check for routes section
        if '## Routes' not in content:
            self._add_error(doc_file, "Missing required 'Routes' section")

    def _validate_content_sections(self, doc_file: Path, content: str):
        """Validate content sections for completeness."""
        # Extract all route sections
        route_sections = re.findall(r'### Route Name: (.+)', content)

        if not route_sections:
            self._add_warning(doc_file, "No route sections found")
            return

        for route_name in route_sections:
            self._validate_route_section(doc_file, content, route_name)

    def _validate_route_section(self, doc_file: Path, content: str, route_name: str):
        """Validate a specific route section."""
        # Find the route section content
        pattern = f'### Route Name: {re.escape(route_name)}(.+?)(?=### Route Name:|$)'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            self._add_error(doc_file, f"Could not find content for route: {route_name}")
            return

        route_content = match.group(1)

        # Check for required subsections
        required_subsections = [
            '#### Metadata',
            '#### Description',
            '#### Workflow Integration',
            '#### Parameters',
            '#### Responses',
            '#### Security Considerations',
            '#### Examples'
        ]

        for subsection in required_subsections:
            if subsection not in route_content:
                self._add_error(doc_file, f"Route '{route_name}' missing required subsection: {subsection}")

        # Validate metadata section
        self._validate_metadata_section(doc_file, route_content, route_name)

        # Validate examples section
        self._validate_examples_section(doc_file, route_content, route_name)

    def _validate_metadata_section(self, doc_file: Path, route_content: str, route_name: str):
        """Validate the metadata section of a route."""
        metadata_pattern = r'#### Metadata(.+?)(?=####|$)'
        match = re.search(metadata_pattern, route_content, re.DOTALL)

        if not match:
            return

        metadata_content = match.group(1)

        # Required metadata fields
        required_fields = [
            'Blueprint',
            'Function',
            'Authentication',
            'User Types',
            'Rate Limiting'
        ]

        for field in required_fields:
            if f'**{field}**:' not in metadata_content:
                self._add_error(doc_file, f"Route '{route_name}' missing metadata field: {field}")

    def _validate_examples_section(self, doc_file: Path, route_content: str, route_name: str):
        """Validate the examples section of a route."""
        examples_pattern = r'#### Examples(.+?)(?=####|$)'
        match = re.search(examples_pattern, route_content, re.DOTALL)

        if not match:
            return

        examples_content = match.group(1)

        # Check for cURL example
        if '##### cURL Example' not in examples_content:
            self._add_warning(doc_file, f"Route '{route_name}' missing cURL example")

        # Check for JavaScript example
        if '##### JavaScript Example' not in examples_content:
            self._add_warning(doc_file, f"Route '{route_name}' missing JavaScript example")

        # Validate code blocks
        code_blocks = re.findall(r'```(\w+)?\n(.+?)\n```', examples_content, re.DOTALL)

        for lang, code in code_blocks:
            if lang == 'bash' and 'curl' in code:
                # Basic cURL validation
                if 'http://localhost:8084' not in code and 'https://' not in code:
                    self._add_warning(doc_file, f"Route '{route_name}' cURL example may be missing URL")

            elif lang == 'javascript' and 'fetch' in code:
                # Basic JavaScript validation
                if 'fetch(' not in code:
                    self._add_warning(doc_file, f"Route '{route_name}' JavaScript example may be malformed")

    def _validate_markdown_format(self, doc_file: Path, content: str):
        """Validate markdown formatting consistency."""
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for consistent heading format
            if line.startswith('#'):
                if not line.startswith('# ') and not line.startswith('## ') and \
                        not line.startswith('### ') and not line.startswith('#### ') and \
                        not line.startswith('##### '):
                    self._add_warning(doc_file, f"Line {i}: Inconsistent heading format")

            # Check for proper list formatting
            if line.startswith('-') and not line.startswith('- '):
                self._add_warning(doc_file, f"Line {i}: List item should have space after dash")

            # Check for proper bold formatting
            if '**' in line:
                bold_count = line.count('**')
                if bold_count % 2 != 0:
                    self._add_warning(doc_file, f"Line {i}: Unmatched bold formatting")

    def _validate_cross_references(self, doc_file: Path, content: str):
        """Validate cross-references and links."""
        # Find all markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

        for link_text, link_url in links:
            # Check internal documentation links
            if link_url.endswith('.md') and not link_url.startswith('http'):
                # Convert relative path to absolute
                if link_url.startswith('/'):
                    link_path = self.docs_dir / link_url[1:]
                else:
                    link_path = doc_file.parent / link_url

                if not link_path.exists():
                    self._add_error(doc_file, f"Broken internal link: {link_url}")

            # Check for placeholder links
            if link_url in ['#', '', 'TODO', 'TBD']:
                self._add_warning(doc_file, f"Placeholder link found: [{link_text}]({link_url})")

    def _generate_statistics(self, doc_files: List[Path]):
        """Generate validation statistics."""
        self.validation_results['stats'] = {
            'total_files': len(doc_files),
            'files_with_errors': len(set(error['file'] for error in self.validation_results['errors'])),
            'files_with_warnings': len(set(warning['file'] for warning in self.validation_results['warnings'])),
            'total_errors': len(self.validation_results['errors']),
            'total_warnings': len(self.validation_results['warnings']),
            'total_info': len(self.validation_results['info'])
        }

        # Calculate coverage statistics
        categories = set()
        for doc_file in doc_files:
            category = self._get_category_from_path(doc_file)
            categories.add(category)

        self.validation_results['stats']['categories_documented'] = len(categories)

    def _get_category_from_path(self, doc_file: Path) -> str:
        """Extract category from documentation file path."""
        parts = doc_file.parts
        if 'documentation' in parts:
            doc_index = parts.index('documentation')
            if doc_index + 1 < len(parts):
                return parts[doc_index + 1]
        return 'unknown'

    def _add_error(self, file_path: Path, message: str):
        """Add an error to the validation results."""
        self.validation_results['errors'].append({
            'file': str(file_path),
            'message': message,
            'type': 'error'
        })

    def _add_warning(self, file_path: Path, message: str):
        """Add a warning to the validation results."""
        self.validation_results['warnings'].append({
            'file': str(file_path),
            'message': message,
            'type': 'warning'
        })

    def _add_info(self, file_path: Path, message: str):
        """Add an info message to the validation results."""
        self.validation_results['info'].append({
            'file': str(file_path),
            'message': message,
            'type': 'info'
        })

    def print_validation_report(self):
        """Print a formatted validation report."""
        results = self.validation_results
        stats = results['stats']

        print("Documentation Validation Report")
        print("=" * 50)
        print(f"Total files: {stats['total_files']}")
        print(f"Categories documented: {stats['categories_documented']}")
        print(f"Files with errors: {stats['files_with_errors']}")
        print(f"Files with warnings: {stats['files_with_warnings']}")
        print(f"Total errors: {stats['total_errors']}")
        print(f"Total warnings: {stats['total_warnings']}")
        print()

        # Print errors
        if results['errors']:
            print("ERRORS:")
            print("-" * 20)
            for error in results['errors']:
                print(f"  {error['file']}: {error['message']}")
            print()

        # Print warnings
        if results['warnings']:
            print("WARNINGS:")
            print("-" * 20)
            for warning in results['warnings']:
                print(f"  {warning['file']}: {warning['message']}")
            print()

        # Print summary
        if stats['total_errors'] == 0:
            print("✅ No errors found!")
        else:
            print(f"❌ {stats['total_errors']} errors need to be fixed")

        if stats['total_warnings'] == 0:
            print("✅ No warnings!")
        else:
            print(f"⚠️  {stats['total_warnings']} warnings to consider")

    def save_validation_report(self, output_file: str = "validation_report.json"):
        """Save validation results to a JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)

        print(f"Validation report saved to {output_file}")


def main():
    """Main function to run documentation validation."""
    validator = DocumentationValidator()

    print("Validating route documentation...")
    results = validator.validate_all_documentation()
    validator.print_validation_report()
    validator.save_validation_report()

    return results


if __name__ == "__main__":
    main()
