#!/usr/bin/env python3
"""
JobFinders Route Validator

This script validates template links against discovered backend routes
and generates correction suggestions for invalid or hardcoded URLs.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs
from difflib import SequenceMatcher


@dataclass
class ValidationResult:
    """Result of validating a link against routes"""
    is_valid: bool
    matched_route: Optional[Dict]
    issues: List[str]
    suggestions: List['CorrectionSuggestion']
    confidence_score: float
    validation_type: str  # 'exact_match', 'pattern_match', 'fuzzy_match', 'no_match'


@dataclass
class CorrectionSuggestion:
    """Suggestion for correcting a link"""
    original_url: str
    suggested_url_for: str
    route_info: Dict
    required_parameters: List[str]
    confidence: float
    reasoning: str
    template_context: str


class RouteValidator:
    """Validator for matching template links to backend routes"""

    def __init__(self, route_mapping_file: str = 'docs/route_mapping.json'):
        self.project_root = Path.cwd()
        self.route_mapping_file = self.project_root / route_mapping_file
        self.routes: Dict[str, Dict] = {}
        self.route_patterns: Dict[str, str] = {}
        self.blueprint_routes: Dict[str, List[str]] = {}

        self.load_route_mapping()
        self._build_route_patterns()

    def load_route_mapping(self):
        """Load route mapping from JSON file"""
        try:
            with open(self.route_mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)

            self.routes = mapping.get('all_routes', {})
            self.blueprint_routes = mapping.get('routes_by_blueprint', {})

            print(f"Loaded {len(self.routes)} routes from {self.route_mapping_file}")

        except FileNotFoundError:
            print(f"Route mapping file not found: {self.route_mapping_file}")
            print("Please run route_discovery.py first to generate route mapping.")
        except Exception as e:
            print(f"Error loading route mapping: {e}")

    def _build_route_patterns(self):
        """Build regex patterns for route matching"""
        for endpoint, route_info in self.routes.items():
            rule = route_info.get('rule', '')
            if rule:
                # Convert Flask route pattern to regex
                pattern = self._flask_rule_to_regex(rule)
                self.route_patterns[endpoint] = pattern

    def _flask_rule_to_regex(self, rule: str) -> str:
        """Convert Flask route rule to regex pattern"""
        # Replace Flask parameters with regex groups
        # <id> -> (\d+) for integers
        # <string:name> -> ([^/]+) for strings
        # <path:filename> -> (.+) for paths

        pattern = rule

        # Handle typed parameters
        pattern = re.sub(r'<int:(\w+)>', r'(?P<\1>\d+)', pattern)
        pattern = re.sub(r'<float:(\w+)>', r'(?P<\1>\d+\.\d+)', pattern)
        pattern = re.sub(r'<string:(\w+)>', r'(?P<\1>[^/]+)', pattern)
        pattern = re.sub(r'<path:(\w+)>', r'(?P<\1>.+)', pattern)
        pattern = re.sub(r'<uuid:(\w+)>', r'(?P<\1>[0-9a-f-]+)', pattern)

        # Handle untyped parameters (default to string)
        pattern = re.sub(r'<(\w+)>', r'(?P<\1>[^/]+)', pattern)

        # Escape special regex characters
        pattern = pattern.replace('.', '\.')

        # Anchor the pattern
        pattern = f'^{pattern}$'

        return pattern

    def validate_link(self, link_info: Dict) -> ValidationResult:
        """Validate a single link against available routes"""
        url = link_info.get('url', '')

        # Skip external URLs, anchors, and special protocols
        if self._should_skip_validation(url):
            return ValidationResult(
                is_valid=True,
                matched_route=None,
                issues=[],
                suggestions=[],
                confidence_score=1.0,
                validation_type='skipped'
            )

        # Check for exact endpoint match (url_for calls)
        if self._is_url_for_call(url):
            return self._validate_url_for_call(url, link_info)

        # Check for hardcoded URL match
        if self._is_hardcoded_url(url):
            return self._validate_hardcoded_url(url, link_info)

        # Template variable - check if it could be valid
        if self._contains_template_variables(url):
            return self._validate_template_url(url, link_info)

        return ValidationResult(
            is_valid=False,
            matched_route=None,
            issues=[f"Unknown URL format: {url}"],
            suggestions=[],
            confidence_score=0.0,
            validation_type='unknown'
        )

    def _should_skip_validation(self, url: str) -> bool:
        """Check if URL should be skipped from validation"""
        skip_patterns = [
            r'^https?://',  # External URLs
            r'^mailto:',  # Email links
            r'^tel:',  # Phone links
            r'^#',  # Anchors
            r'^javascript:',  # JavaScript
            r'^data:',  # Data URLs
        ]

        return any(re.match(pattern, url) for pattern in skip_patterns)

    def _is_url_for_call(self, url: str) -> bool:
        """Check if URL is a Jinja2 url_for call"""
        return 'url_for(' in url

    def _is_hardcoded_url(self, url: str) -> bool:
        """Check if URL is hardcoded (starts with /)"""
        return url.startswith('/') and not self._contains_template_variables(url)

    def _contains_template_variables(self, url: str) -> bool:
        """Check if URL contains Jinja2 template variables"""
        return '{{' in url or '{%' in url

    def _validate_url_for_call(self, url: str, link_info: Dict) -> ValidationResult:
        """Validate a url_for call"""
        # Extract endpoint from url_for call
        endpoint_match = re.search(r'url_for\([\'"]([^\'"]*)[\'"]', url)

        if not endpoint_match:
            return ValidationResult(
                is_valid=False,
                matched_route=None,
                issues=["Invalid url_for syntax"],
                suggestions=[],
                confidence_score=0.0,
                validation_type='invalid_syntax'
            )

        endpoint = endpoint_match.group(1)

        # Check if endpoint exists
        if endpoint in self.routes:
            route_info = self.routes[endpoint]

            # Check if required parameters are provided
            required_params = route_info.get('parameters', [])
            provided_params = self._extract_url_for_parameters(url)

            missing_params = [p for p in required_params if p not in provided_params]

            if missing_params:
                return ValidationResult(
                    is_valid=False,
                    matched_route=route_info,
                    issues=[f"Missing required parameters: {', '.join(missing_params)}"],
                    suggestions=[],
                    confidence_score=0.5,
                    validation_type='missing_parameters'
                )

            return ValidationResult(
                is_valid=True,
                matched_route=route_info,
                issues=[],
                suggestions=[],
                confidence_score=1.0,
                validation_type='exact_match'
            )

        # Endpoint not found - suggest alternatives
        suggestions = self._suggest_similar_endpoints(endpoint)

        return ValidationResult(
            is_valid=False,
            matched_route=None,
            issues=[f"Endpoint '{endpoint}' not found"],
            suggestions=suggestions,
            confidence_score=0.0,
            validation_type='endpoint_not_found'
        )

    def _validate_hardcoded_url(self, url: str, link_info: Dict) -> ValidationResult:
        """Validate a hardcoded URL"""
        # Parse URL to extract path and parameters
        parsed = urlparse(url)
        path = parsed.path

        # Try to match against route patterns
        best_match = None
        best_score = 0.0

        for endpoint, pattern in self.route_patterns.items():
            match = re.match(pattern, path)
            if match:
                route_info = self.routes[endpoint]

                # Calculate confidence based on parameter extraction
                extracted_params = match.groupdict()
                required_params = route_info.get('parameters', [])

                if set(extracted_params.keys()) == set(required_params):
                    # Perfect match
                    suggestion = self._create_url_for_suggestion(
                        url, endpoint, route_info, extracted_params, 1.0,
                        "Exact pattern match found"
                    )

                    return ValidationResult(
                        is_valid=True,
                        matched_route=route_info,
                        issues=["Using hardcoded URL instead of url_for"],
                        suggestions=[suggestion],
                        confidence_score=1.0,
                        validation_type='pattern_match'
                    )

        # No exact match - try fuzzy matching
        fuzzy_matches = self._find_fuzzy_matches(path)

        if fuzzy_matches:
            suggestions = []
            for endpoint, score in fuzzy_matches[:3]:  # Top 3 matches
                route_info = self.routes[endpoint]
                suggestion = self._create_url_for_suggestion(
                    url, endpoint, route_info, {}, score,
                    f"Fuzzy match (similarity: {score:.2f})"
                )
                suggestions.append(suggestion)

            return ValidationResult(
                is_valid=False,
                matched_route=None,
                issues=[f"No exact route match for '{path}'"],
                suggestions=suggestions,
                confidence_score=fuzzy_matches[0][1],
                validation_type='fuzzy_match'
            )

        return ValidationResult(
            is_valid=False,
            matched_route=None,
            issues=[f"No matching route found for '{path}'"],
            suggestions=[],
            confidence_score=0.0,
            validation_type='no_match'
        )

    def _validate_template_url(self, url: str, link_info: Dict) -> ValidationResult:
        """Validate a URL containing template variables"""
        # This is more complex - we can only provide general guidance
        issues = []
        suggestions = []

        # Check if it looks like it should be a url_for call
        if url.startswith('/') and '{{' in url:
            issues.append("Template URL should probably use url_for() for better maintainability")

            # Try to suggest a conversion
            suggestion = self._suggest_template_url_conversion(url)
            if suggestion:
                suggestions.append(suggestion)

        return ValidationResult(
            is_valid=True,  # Assume valid since we can't fully validate
            matched_route=None,
            issues=issues,
            suggestions=suggestions,
            confidence_score=0.7,
            validation_type='template_variable'
        )

    def _extract_url_for_parameters(self, url_for_call: str) -> List[str]:
        """Extract parameter names from url_for call"""
        # Simple extraction - look for parameter names
        params = []

        # Find parameters after the endpoint
        param_section = re.search(r'url_for\([^,]+,(.*)\)', url_for_call)
        if param_section:
            param_text = param_section.group(1)

            # Extract parameter names (simplified)
            param_matches = re.findall(r'(\w+)\s*=', param_text)
            params.extend(param_matches)

        return params

    def _suggest_similar_endpoints(self, endpoint: str) -> List[CorrectionSuggestion]:
        """Suggest similar endpoints for a non-existent endpoint"""
        suggestions = []

        # Calculate similarity scores
        similarities = []
        for existing_endpoint in self.routes.keys():
            similarity = SequenceMatcher(None, endpoint, existing_endpoint).ratio()
            if similarity > 0.5:  # Only suggest if reasonably similar
                similarities.append((existing_endpoint, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Create suggestions
        for existing_endpoint, similarity in similarities[:3]:
            route_info = self.routes[existing_endpoint]

            suggestion = CorrectionSuggestion(
                original_url=f"url_for('{endpoint}')",
                suggested_url_for=f"url_for('{existing_endpoint}')",
                route_info=route_info,
                required_parameters=route_info.get('parameters', []),
                confidence=similarity,
                reasoning=f"Similar endpoint name (similarity: {similarity:.2f})",
                template_context=""
            )

            suggestions.append(suggestion)

        return suggestions

    def _find_fuzzy_matches(self, path: str) -> List[Tuple[str, float]]:
        """Find fuzzy matches for a path"""
        matches = []

        for endpoint, route_info in self.routes.items():
            route_rule = route_info.get('rule', '')

            # Remove parameter placeholders for comparison
            clean_rule = re.sub(r'<[^>]+>', '', route_rule)
            clean_path = path

            # Calculate similarity
            similarity = SequenceMatcher(None, clean_path, clean_rule).ratio()

            if similarity > 0.6:  # Threshold for fuzzy matching
                matches.append((endpoint, similarity))

        # Sort by similarity
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def _create_url_for_suggestion(self, original_url: str, endpoint: str,
                                   route_info: Dict, extracted_params: Dict,
                                   confidence: float, reasoning: str) -> CorrectionSuggestion:
        """Create a url_for correction suggestion"""
        # Build url_for call
        url_for_parts = [f"'{endpoint}'"]

        # Add parameters
        for param_name, param_value in extracted_params.items():
            # Try to determine if this should be a variable or literal
            if param_value.isdigit():
                # Likely a variable that should be templated
                url_for_parts.append(f"{param_name}={{{{ {param_name} }}}}")
            else:
                url_for_parts.append(f"{param_name}='{param_value}'")

        suggested_url_for = f"{{{{ url_for({', '.join(url_for_parts)}) }}}}"

        return CorrectionSuggestion(
            original_url=original_url,
            suggested_url_for=suggested_url_for,
            route_info=route_info,
            required_parameters=route_info.get('parameters', []),
            confidence=confidence,
            reasoning=reasoning,
            template_context=""
        )

    def _suggest_template_url_conversion(self, url: str) -> Optional[CorrectionSuggestion]:
        """Suggest conversion of template URL to url_for"""
        # This is a simplified suggestion - in practice, this would be more complex
        return CorrectionSuggestion(
            original_url=url,
            suggested_url_for="{{ url_for('endpoint_name', param=value) }}",
            route_info={},
            required_parameters=[],
            confidence=0.5,
            reasoning="Template URL should use url_for for better maintainability",
            template_context=""
        )

    def validate_template_links(self, template_analysis_file: str) -> Dict[str, Any]:
        """Validate all links from template analysis"""
        try:
            with open(template_analysis_file, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
        except FileNotFoundError:
            print(f"Template analysis file not found: {template_analysis_file}")
            return {}

        validation_results = {
            'summary': {
                'total_links': 0,
                'valid_links': 0,
                'invalid_links': 0,
                'links_with_issues': 0,
                'links_with_suggestions': 0
            },
            'templates': {},
            'issues_by_type': {},
            'suggestions': []
        }

        for template_path, template_data in analysis.get('templates', {}).items():
            template_results = {
                'path': template_path,
                'links': [],
                'summary': {
                    'total': 0,
                    'valid': 0,
                    'invalid': 0,
                    'with_issues': 0,
                    'with_suggestions': 0
                }
            }

            for link_data in template_data.get('links', []):
                result = self.validate_link(link_data)

                link_result = {
                    'link': link_data,
                    'validation': asdict(result)
                }

                template_results['links'].append(link_result)

                # Update counters
                template_results['summary']['total'] += 1
                validation_results['summary']['total_links'] += 1

                if result.is_valid:
                    template_results['summary']['valid'] += 1
                    validation_results['summary']['valid_links'] += 1
                else:
                    template_results['summary']['invalid'] += 1
                    validation_results['summary']['invalid_links'] += 1

                if result.issues:
                    template_results['summary']['with_issues'] += 1
                    validation_results['summary']['links_with_issues'] += 1

                    # Categorize issues
                    for issue in result.issues:
                        issue_type = self._categorize_issue(issue)
                        if issue_type not in validation_results['issues_by_type']:
                            validation_results['issues_by_type'][issue_type] = 0
                        validation_results['issues_by_type'][issue_type] += 1

                if result.suggestions:
                    template_results['summary']['with_suggestions'] += 1
                    validation_results['summary']['links_with_suggestions'] += 1

                    # Add to global suggestions
                    for suggestion in result.suggestions:
                        validation_results['suggestions'].append({
                            'template': template_path,
                            'line': link_data.get('line_number', 0),
                            'suggestion': asdict(suggestion)
                        })

            validation_results['templates'][template_path] = template_results

        return validation_results

    def _categorize_issue(self, issue: str) -> str:
        """Categorize an issue by type"""
        if "hardcoded" in issue.lower():
            return "hardcoded_urls"
        elif "missing" in issue.lower() and "parameter" in issue.lower():
            return "missing_parameters"
        elif "not found" in issue.lower():
            return "endpoint_not_found"
        elif "invalid" in issue.lower() and "syntax" in issue.lower():
            return "invalid_syntax"
        else:
            return "other"

    def generate_correction_report(self, validation_results: Dict) -> Dict[str, Any]:
        """Generate a comprehensive correction report"""
        report = {
            'summary': validation_results.get('summary', {}),
            'priority_fixes': [],
            'bulk_corrections': {},
            'template_specific_fixes': {},
            'migration_plan': []
        }

        # Identify priority fixes
        high_priority_issues = ['endpoint_not_found', 'invalid_syntax', 'missing_parameters']

        for template_path, template_data in validation_results.get('templates', {}).items():
            template_fixes = []

            for link_result in template_data.get('links', []):
                validation = link_result.get('validation', {})

                if not validation.get('is_valid', True) or validation.get('issues', []):
                    # Categorize by priority
                    issue_types = [self._categorize_issue(issue) for issue in validation.get('issues', [])]

                    if any(issue_type in high_priority_issues for issue_type in issue_types):
                        priority = 'high'
                    elif 'hardcoded_urls' in issue_types:
                        priority = 'medium'
                    else:
                        priority = 'low'

                    fix_item = {
                        'template': template_path,
                        'line': link_result['link'].get('line_number', 0),
                        'url': link_result['link'].get('url', ''),
                        'issues': validation.get('issues', []),
                        'suggestions': validation.get('suggestions', []),
                        'priority': priority,
                        'confidence': validation.get('confidence_score', 0.0)
                    }

                    template_fixes.append(fix_item)

                    if priority == 'high':
                        report['priority_fixes'].append(fix_item)

            if template_fixes:
                report['template_specific_fixes'][template_path] = template_fixes

        # Generate bulk correction patterns
        self._generate_bulk_corrections(report, validation_results)

        # Create migration plan
        self._create_migration_plan(report)

        return report

    def _generate_bulk_corrections(self, report: Dict, validation_results: Dict):
        """Generate bulk correction patterns"""
        # Group similar corrections
        correction_patterns = {}

        for suggestion_data in validation_results.get('suggestions', []):
            suggestion = suggestion_data.get('suggestion', {})
            original = suggestion.get('original_url', '')
            suggested = suggestion.get('suggested_url_for', '')

            # Create pattern key
            pattern_key = self._create_pattern_key(original, suggested)

            if pattern_key not in correction_patterns:
                correction_patterns[pattern_key] = {
                    'pattern': pattern_key,
                    'original_pattern': original,
                    'suggested_pattern': suggested,
                    'occurrences': [],
                    'confidence': suggestion.get('confidence', 0.0)
                }

            correction_patterns[pattern_key]['occurrences'].append({
                'template': suggestion_data.get('template', ''),
                'line': suggestion_data.get('line', 0),
                'original_url': original
            })

        # Filter patterns with multiple occurrences
        bulk_patterns = {k: v for k, v in correction_patterns.items()
                         if len(v['occurrences']) > 1}

        report['bulk_corrections'] = bulk_patterns

    def _create_pattern_key(self, original: str, suggested: str) -> str:
        """Create a pattern key for grouping similar corrections"""
        # Simplified pattern creation
        # Remove specific values and create a general pattern
        pattern = original

        # Replace numbers with placeholder
        pattern = re.sub(r'\d+', '{id}', pattern)

        # Replace common variable patterns
        pattern = re.sub(r'{{[^}]+}}', '{var}', pattern)

        return pattern

    def _create_migration_plan(self, report: Dict):
        """Create a step-by-step migration plan"""
        plan = []

        # Step 1: Fix high priority issues
        if report['priority_fixes']:
            plan.append({
                'step': 1,
                'title': 'Fix Critical Issues',
                'description': 'Address broken routes and invalid syntax',
                'items': len(report['priority_fixes']),
                'estimated_time': f"{len(report['priority_fixes']) * 5} minutes"
            })

        # Step 2: Apply bulk corrections
        if report['bulk_corrections']:
            total_bulk_items = sum(len(pattern['occurrences'])
                                   for pattern in report['bulk_corrections'].values())
            plan.append({
                'step': 2,
                'title': 'Apply Bulk Corrections',
                'description': 'Convert hardcoded URLs to url_for calls',
                'items': total_bulk_items,
                'estimated_time': f"{len(report['bulk_corrections']) * 10} minutes"
            })

        # Step 3: Template-specific fixes
        remaining_fixes = sum(len(fixes) for fixes in report['template_specific_fixes'].values())
        remaining_fixes -= len(report['priority_fixes'])
        if report['bulk_corrections']:
            remaining_fixes -= sum(len(pattern['occurrences'])
                                   for pattern in report['bulk_corrections'].values())

        if remaining_fixes > 0:
            plan.append({
                'step': 3,
                'title': 'Template-Specific Fixes',
                'description': 'Address remaining template-specific issues',
                'items': remaining_fixes,
                'estimated_time': f"{remaining_fixes * 3} minutes"
            })

        report['migration_plan'] = plan

    def save_validation_results(self, validation_results: Dict, correction_report: Dict,
                                output_dir: str = 'docs'):
        """Save validation results and correction report"""
        output_path = Path(self.project_root) / output_dir
        output_path.mkdir(exist_ok=True)

        # Save validation results
        with open(output_path / 'route_validation_results.json', 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)

        # Save correction report
        with open(output_path / 'route_correction_report.json', 'w', encoding='utf-8') as f:
            json.dump(correction_report, f, indent=2, ensure_ascii=False)

        print(f"Validation results saved to {output_path}")
        return output_path


def main():
    """Main function to run route validation"""
    print("JobFinders Route Validator")
    print("=" * 40)

    # Initialize validator
    validator = RouteValidator()

    if not validator.routes:
        print("No routes loaded. Please run route_discovery.py first.")
        return

    # Validate old templates
    print("\nValidating old templates...")
    old_validation = validator.validate_template_links('docs/old_templates_analysis.json')

    # Validate new templates
    print("Validating new templates...")
    new_validation = validator.validate_template_links('docs/new_templates_analysis.json')

    # Generate correction reports
    print("Generating correction reports...")
    old_correction_report = validator.generate_correction_report(old_validation)
    new_correction_report = validator.generate_correction_report(new_validation)

    # Save results
    validator.save_validation_results(
        {'old_templates': old_validation, 'new_templates': new_validation},
        {'old_templates': old_correction_report, 'new_templates': new_correction_report}
    )

    # Print summary
    print("\nValidation Summary:")
    print(f"Old Templates:")
    print(f"  Total Links: {old_validation['summary']['total_links']}")
    print(f"  Valid: {old_validation['summary']['valid_links']}")
    print(f"  Invalid: {old_validation['summary']['invalid_links']}")
    print(f"  With Issues: {old_validation['summary']['links_with_issues']}")
    print(f"  With Suggestions: {old_validation['summary']['links_with_suggestions']}")

    print(f"\nNew Templates:")
    print(f"  Total Links: {new_validation['summary']['total_links']}")
    print(f"  Valid: {new_validation['summary']['valid_links']}")
    print(f"  Invalid: {new_validation['summary']['invalid_links']}")
    print(f"  With Issues: {new_validation['summary']['links_with_issues']}")
    print(f"  With Suggestions: {new_validation['summary']['links_with_suggestions']}")

    # Show priority fixes
    if old_correction_report['priority_fixes']:
        print(f"\nOld Templates - Priority Fixes: {len(old_correction_report['priority_fixes'])}")

    if new_correction_report['priority_fixes']:
        print(f"New Templates - Priority Fixes: {len(new_correction_report['priority_fixes'])}")

    print("\nValidation complete. Check docs/ for detailed reports.")


if __name__ == '__main__':
    main()
