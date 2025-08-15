#!/usr/bin/env python3
"""
Template Link Parser for JobFinders Template Route Validation

This script parses Jinja2 templates to extract all links, form actions, and URL patterns
for validation against the discovered Flask routes.

Usage:
    python scripts/template_parser.py [--output template_links.json] [--format json|yaml|csv]
"""

import json
import yaml
import csv
import os
import re
import sys
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import html

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class LinkInfo:
    """Data class for link information extracted from templates"""
    url: str
    element_type: str  # 'a', 'form', 'img', 'script', 'link', etc.
    context: str  # surrounding HTML context
    line_number: int
    file_path: str
    is_external: bool
    is_hardcoded: bool
    uses_url_for: bool
    url_for_endpoint: Optional[str]
    url_for_parameters: Dict[str, str]
    query_parameters: Dict[str, str]
    fragment: Optional[str]
    template_variables: List[str]
    conditional_context: Optional[str]  # if inside {% if %} block
    loop_context: Optional[str]  # if inside {% for %} block


@dataclass
class TemplateAnalysis:
    """Analysis results for a single template"""
    file_path: str
    total_links: int
    url_for_links: int
    hardcoded_links: int
    external_links: int
    broken_links: int
    template_extends: Optional[str]
    template_includes: List[str]
    template_blocks: List[str]
    template_variables: Set[str]
    links: List[LinkInfo]


class TemplateLinkParser:
    """Parser for extracting links from Jinja2 templates"""

    def __init__(self, template_dir: str = "template"):
        self.template_dir = Path(template_dir)
        self.analyses: Dict[str, TemplateAnalysis] = {}

        # Regex patterns for different link types
        self.patterns = {
            'url_for': re.compile(r'{{\s*url_for\([\'"]([^\'"]+)[\'"](?:,\s*([^}]+))?\)\s*}}'),
            'href_links': re.compile(r'href\s*=\s*[\'"]([^\'"]*)[\'"]', re.IGNORECASE),
            'form_actions': re.compile(r'action\s*=\s*[\'"]([^\'"]*)[\'"]', re.IGNORECASE),
            'img_src': re.compile(r'src\s*=\s*[\'"]([^\'"]*)[\'"]', re.IGNORECASE),
            'script_src': re.compile(r'<script[^>]+src\s*=\s*[\'"]([^\'"]*)[\'"]', re.IGNORECASE),
            'link_href': re.compile(r'<link[^>]+href\s*=\s*[\'"]([^\'"]*)[\'"]', re.IGNORECASE),
            'template_vars': re.compile(r'{{\s*([^}]+)\s*}}'),
            'template_extends': re.compile(r'{%\s*extends\s+[\'"]([^\'"]+)[\'"]'),
            'template_includes': re.compile(r'{%\s*include\s+[\'"]([^\'"]+)[\'"]'),
            'template_blocks': re.compile(r'{%\s*block\s+(\w+)\s*%}'),
            'conditional_blocks': re.compile(r'{%\s*if\s+([^%]+)\s*%}'),
            'loop_blocks': re.compile(r'{%\s*for\s+([^%]+)\s*%}'),
        }

    def parse_all_templates(self) -> Dict[str, TemplateAnalysis]:
        """Parse all templates in the template directory"""
        print("🔍 Parsing all templates...")

        template_files = list(self.template_dir.rglob("*.html"))
        print(f"Found {len(template_files)} template files")

        for template_file in template_files:
            try:
                analysis = self._parse_template(template_file)
                rel_path = str(template_file.relative_to(self.template_dir))
                self.analyses[rel_path] = analysis
                print(f"✅ Parsed {rel_path}: {analysis.total_links} links found")
            except Exception as e:
                print(f"❌ Error parsing {template_file}: {e}")

        print(f"✅ Completed parsing {len(self.analyses)} templates")
        return self.analyses

    def _parse_template(self, template_file: Path) -> TemplateAnalysis:
        """Parse a single template file"""
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()

        rel_path = str(template_file.relative_to(self.template_dir))
        lines = content.split('\n')

        # Extract template metadata
        extends = self._extract_extends(content)
        includes = self._extract_includes(content)
        blocks = self._extract_blocks(content)
        variables = self._extract_template_variables(content)

        # Extract all links
        links = []

        # Parse different types of links
        links.extend(self._extract_href_links(content, lines, rel_path))
        links.extend(self._extract_form_actions(content, lines, rel_path))
        links.extend(self._extract_img_sources(content, lines, rel_path))
        links.extend(self._extract_script_sources(content, lines, rel_path))
        links.extend(self._extract_link_hrefs(content, lines, rel_path))

        # Calculate statistics
        total_links = len(links)
        url_for_links = sum(1 for link in links if link.uses_url_for)
        hardcoded_links = sum(1 for link in links if link.is_hardcoded)
        external_links = sum(1 for link in links if link.is_external)
        broken_links = 0  # Will be calculated during validation

        return TemplateAnalysis(
            file_path=rel_path,
            total_links=total_links,
            url_for_links=url_for_links,
            hardcoded_links=hardcoded_links,
            external_links=external_links,
            broken_links=broken_links,
            template_extends=extends,
            template_includes=includes,
            template_blocks=blocks,
            template_variables=variables,
            links=links
        )

    def _extract_href_links(self, content: str, lines: List[str], file_path: str) -> List[LinkInfo]:
        """Extract href links from anchor tags"""
        links = []

        for match in self.patterns['href_links'].finditer(content):
            url = match.group(1)
            line_num = self._get_line_number(content, match.start())
            context = self._get_context(lines, line_num)

            link_info = self._analyze_url(
                url=url,
                element_type='a',
                context=context,
                line_number=line_num,
                file_path=file_path
            )
            links.append(link_info)

        return links

    def _extract_form_actions(self, content: str, lines: List[str], file_path: str) -> List[LinkInfo]:
        """Extract form action URLs"""
        links = []

        for match in self.patterns['form_actions'].finditer(content):
            url = match.group(1)
            line_num = self._get_line_number(content, match.start())
            context = self._get_context(lines, line_num)

            link_info = self._analyze_url(
                url=url,
                element_type='form',
                context=context,
                line_number=line_num,
                file_path=file_path
            )
            links.append(link_info)

        return links

    def _extract_img_sources(self, content: str, lines: List[str], file_path: str) -> List[LinkInfo]:
        """Extract image source URLs"""
        links = []

        for match in self.patterns['img_src'].finditer(content):
            url = match.group(1)
            line_num = self._get_line_number(content, match.start())
            context = self._get_context(lines, line_num)

            link_info = self._analyze_url(
                url=url,
                element_type='img',
                context=context,
                line_number=line_num,
                file_path=file_path
            )
            links.append(link_info)

        return links

    def _extract_script_sources(self, content: str, lines: List[str], file_path: str) -> List[LinkInfo]:
        """Extract script source URLs"""
        links = []

        for match in self.patterns['script_src'].finditer(content):
            url = match.group(1)
            line_num = self._get_line_number(content, match.start())
            context = self._get_context(lines, line_num)

            link_info = self._analyze_url(
                url=url,
                element_type='script',
                context=context,
                line_number=line_num,
                file_path=file_path
            )
            links.append(link_info)

        return links

    def _extract_link_hrefs(self, content: str, lines: List[str], file_path: str) -> List[LinkInfo]:
        """Extract link tag hrefs (CSS, etc.)"""
        links = []

        for match in self.patterns['link_href'].finditer(content):
            url = match.group(1)
            line_num = self._get_line_number(content, match.start())
            context = self._get_context(lines, line_num)

            link_info = self._analyze_url(
                url=url,
                element_type='link',
                context=context,
                line_number=line_num,
                file_path=file_path
            )
            links.append(link_info)

        return links

    def _analyze_url(self, url: str, element_type: str, context: str,
                     line_number: int, file_path: str) -> LinkInfo:
        """Analyze a URL and extract metadata"""

        # Check if it's a url_for call
        uses_url_for = 'url_for(' in url
        url_for_endpoint = None
        url_for_parameters = {}

        if uses_url_for:
            url_for_match = self.patterns['url_for'].search(url)
            if url_for_match:
                url_for_endpoint = url_for_match.group(1)
                params_str = url_for_match.group(2)
                if params_str:
                    url_for_parameters = self._parse_url_for_parameters(params_str)

        # Extract template variables
        template_variables = []
        for var_match in self.patterns['template_vars'].finditer(url):
            template_variables.append(var_match.group(1).strip())

        # Parse URL components
        parsed_url = urlparse(url) if not uses_url_for else None
        query_parameters = {}
        fragment = None

        if parsed_url:
            query_parameters = parse_qs(parsed_url.query)
            fragment = parsed_url.fragment

        # Determine URL type
        is_external = self._is_external_url(url)
        is_hardcoded = self._is_hardcoded_url(url)

        # Get conditional and loop context
        conditional_context = self._get_conditional_context(context)
        loop_context = self._get_loop_context(context)

        return LinkInfo(
            url=url,
            element_type=element_type,
            context=context,
            line_number=line_number,
            file_path=file_path,
            is_external=is_external,
            is_hardcoded=is_hardcoded,
            uses_url_for=uses_url_for,
            url_for_endpoint=url_for_endpoint,
            url_for_parameters=url_for_parameters,
            query_parameters=query_parameters,
            fragment=fragment,
            template_variables=template_variables,
            conditional_context=conditional_context,
            loop_context=loop_context
        )

    def _is_external_url(self, url: str) -> bool:
        """Check if URL is external"""
        if url.startswith(('http://', 'https://', '//')):
            return True
        if url.startswith('mailto:') or url.startswith('tel:'):
            return True
        return False

    def _is_hardcoded_url(self, url: str) -> bool:
        """Check if URL is hardcoded (not using url_for)"""
        if 'url_for(' in url:
            return False
        if self._is_external_url(url):
            return False
        if url.startswith('/') and not url.startswith('//'):
            return True
        return False

    def _parse_url_for_parameters(self, params_str: str) -> Dict[str, str]:
        """Parse url_for parameters"""
        parameters = {}
        # Simple parameter parsing - could be enhanced
        param_pairs = params_str.split(',')
        for pair in param_pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                parameters[key.strip()] = value.strip()
        return parameters

    def _extract_extends(self, content: str) -> Optional[str]:
        """Extract template extends"""
        match = self.patterns['template_extends'].search(content)
        return match.group(1) if match else None

    def _extract_includes(self, content: str) -> List[str]:
        """Extract template includes"""
        return [match.group(1) for match in self.patterns['template_includes'].finditer(content)]

    def _extract_blocks(self, content: str) -> List[str]:
        """Extract template blocks"""
        return [match.group(1) for match in self.patterns['template_blocks'].finditer(content)]

    def _extract_template_variables(self, content: str) -> Set[str]:
        """Extract template variables"""
        variables = set()
        for match in self.patterns['template_vars'].finditer(content):
            var_content = match.group(1).strip()
            # Extract variable names (simple parsing)
            if '.' in var_content:
                base_var = var_content.split('.')[0]
                variables.add(base_var)
            elif '(' not in var_content:  # Skip function calls
                variables.add(var_content)
        return variables

    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number for a position in content"""
        return content[:position].count('\n') + 1

    def _get_context(self, lines: List[str], line_num: int, context_lines: int = 2) -> str:
        """Get surrounding context for a line"""
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        context_lines_list = lines[start:end]
        return '\n'.join(context_lines_list)

    def _get_conditional_context(self, context: str) -> Optional[str]:
        """Extract conditional context (if blocks)"""
        if_match = self.patterns['conditional_blocks'].search(context)
        return if_match.group(1).strip() if if_match else None

    def _get_loop_context(self, context: str) -> Optional[str]:
        """Extract loop context (for blocks)"""
        for_match = self.patterns['loop_blocks'].search(context)
        return for_match.group(1).strip() if for_match else None

    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_templates = len(self.analyses)
        total_links = sum(analysis.total_links for analysis in self.analyses.values())
        total_url_for = sum(analysis.url_for_links for analysis in self.analyses.values())
        total_hardcoded = sum(analysis.hardcoded_links for analysis in self.analyses.values())
        total_external = sum(analysis.external_links for analysis in self.analyses.values())

        # Template categories
        template_categories = {}
        for file_path, analysis in self.analyses.items():
            category = file_path.split('/')[0] if '/' in file_path else 'root'
            if category not in template_categories:
                template_categories[category] = {
                    'count': 0,
                    'total_links': 0,
                    'url_for_links': 0,
                    'hardcoded_links': 0
                }
            template_categories[category]['count'] += 1
            template_categories[category]['total_links'] += analysis.total_links
            template_categories[category]['url_for_links'] += analysis.url_for_links
            template_categories[category]['hardcoded_links'] += analysis.hardcoded_links

        # Most problematic templates
        problematic_templates = sorted(
            [(path, analysis) for path, analysis in self.analyses.items()],
            key=lambda x: x[1].hardcoded_links,
            reverse=True
        )[:10]

        return {
            'metadata': {
                'total_templates': total_templates,
                'total_links': total_links,
                'total_url_for_links': total_url_for,
                'total_hardcoded_links': total_hardcoded,
                'total_external_links': total_external,
                'url_for_percentage': (total_url_for / total_links * 100) if total_links > 0 else 0,
                'hardcoded_percentage': (total_hardcoded / total_links * 100) if total_links > 0 else 0
            },
            'template_categories': template_categories,
            'problematic_templates': [
                {
                    'file_path': path,
                    'hardcoded_links': analysis.hardcoded_links,
                    'total_links': analysis.total_links,
                    'hardcoded_percentage': (
                                analysis.hardcoded_links / analysis.total_links * 100) if analysis.total_links > 0 else 0
                }
                for path, analysis in problematic_templates
            ]
        }


class TemplateReporter:
    """Generate reports from template analysis results"""

    def __init__(self, analyses: Dict[str, TemplateAnalysis]):
        self.analyses = analyses

    def save_json(self, output_path: str):
        """Save analysis results as JSON"""
        print(f"💾 Saving JSON report to {output_path}")

        # Convert analyses to serializable format
        serializable_data = {}
        for path, analysis in self.analyses.items():
            serializable_data[path] = {
                **asdict(analysis),
                'template_variables': list(analysis.template_variables)
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

    def save_csv(self, output_path: str):
        """Save link analysis as CSV"""
        print(f"💾 Saving CSV report to {output_path}")

        fieldnames = [
            'file_path', 'line_number', 'element_type', 'url', 'uses_url_for',
            'url_for_endpoint', 'is_hardcoded', 'is_external', 'context'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for analysis in self.analyses.values():
                for link in analysis.links:
                    writer.writerow({
                        'file_path': link.file_path,
                        'line_number': link.line_number,
                        'element_type': link.element_type,
                        'url': link.url,
                        'uses_url_for': link.uses_url_for,
                        'url_for_endpoint': link.url_for_endpoint,
                        'is_hardcoded': link.is_hardcoded,
                        'is_external': link.is_external,
                        'context': link.context.replace('\n', ' ')
                    })

    def print_summary(self, parser: TemplateLinkParser):
        """Print summary of template analysis"""
        summary = parser.generate_summary()
        metadata = summary['metadata']

        print("\n" + "=" * 60)
        print("📊 TEMPLATE LINK ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total Templates: {metadata['total_templates']}")
        print(f"Total Links: {metadata['total_links']}")
        print(f"URL_FOR Links: {metadata['total_url_for_links']} ({metadata['url_for_percentage']:.1f}%)")
        print(f"Hardcoded Links: {metadata['total_hardcoded_links']} ({metadata['hardcoded_percentage']:.1f}%)")
        print(f"External Links: {metadata['total_external_links']}")

        print("\n📂 Template Categories:")
        for category, stats in summary['template_categories'].items():
            print(
                f"  {category:20} {stats['count']:3d} templates, {stats['total_links']:4d} links ({stats['hardcoded_links']} hardcoded)")

        print("\n⚠️  Most Problematic Templates:")
        for template in summary['problematic_templates'][:5]:
            if template['hardcoded_links'] > 0:
                print(
                    f"  {template['file_path']:40} {template['hardcoded_links']:3d} hardcoded ({template['hardcoded_percentage']:.1f}%)")


def main():
    """Main function to run template parsing"""
    import argparse

    parser = argparse.ArgumentParser(description='Parse templates and extract links')
    parser.add_argument('--template-dir', '-t', default='template',
                        help='Template directory path (default: template)')
    parser.add_argument('--output', '-o', default='template_links.json',
                        help='Output file path (default: template_links.json)')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--summary', '-s', action='store_true',
                        help='Print summary to console')

    args = parser.parse_args()

    try:
        print("🚀 Starting Template Link Analysis for JobFinders")
        print("-" * 50)

        # Parse templates
        template_parser = TemplateLinkParser(args.template_dir)
        analyses = template_parser.parse_all_templates()

        # Generate report
        reporter = TemplateReporter(analyses)

        # Save output
        if args.format == 'json':
            reporter.save_json(args.output)
        elif args.format == 'csv':
            reporter.save_csv(args.output)

        # Print summary if requested
        if args.summary:
            reporter.print_summary(template_parser)

        print(f"\n✅ Template analysis completed successfully!")
        print(f"📄 Report saved to: {args.output}")

    except Exception as e:
        print(f"❌ Error during template analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
