#!/usr/bin/env python3
"""
Route Discovery Script for JobFinders Template Route Validation

This script discovers and catalogs all Flask routes in the JobFinders application,
extracting metadata including endpoints, methods, parameters, and authentication requirements.

Usage:
    python scripts/route_discovery.py [--output route_mapping.json] [--format json|yaml|csv]
"""

import json
import yaml
import csv
import sys
import os
import inspect
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask
from werkzeug.routing import Rule
from src.config import config_instance
from src.main import create_app


@dataclass
class RouteInfo:
    """Data class for route information"""
    endpoint: str
    rule: str
    methods: List[str]
    blueprint: Optional[str]
    view_function: str
    module: str
    parameters: List[str]
    auth_required: bool
    roles_required: List[str]
    description: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]


class RouteDiscoveryEngine:
    """Engine for discovering and analyzing Flask routes"""

    def __init__(self, app: Flask):
        self.app = app
        self.routes: Dict[str, RouteInfo] = {}
        self.blueprint_routes: Dict[str, List[RouteInfo]] = {}

    def discover_routes(self) -> Dict[str, RouteInfo]:
        """Discover all routes in the Flask application"""
        print("🔍 Discovering Flask routes...")

        for rule in self.app.url_map.iter_rules():
            route_info = self._analyze_route(rule)
            if route_info:
                self.routes[route_info.endpoint] = route_info

        print(f"✅ Discovered {len(self.routes)} routes")
        return self.routes

    def _analyze_route(self, rule: Rule) -> Optional[RouteInfo]:
        """Analyze a single route rule and extract metadata"""
        try:
            # Get view function
            view_function = self.app.view_functions.get(rule.endpoint)
            if not view_function:
                return None

            # Extract basic information
            endpoint = rule.endpoint
            blueprint = endpoint.split('.')[0] if '.' in endpoint else None
            methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]

            # Extract parameters from rule
            parameters = self._extract_parameters(rule.rule)

            # Get function information
            module = view_function.__module__ if view_function else 'unknown'
            view_name = view_function.__name__ if view_function else 'unknown'

            # Get file path and line number
            file_path, line_number = self._get_function_location(view_function)

            # Analyze authentication requirements
            auth_required, roles_required = self._analyze_auth_requirements(view_function)

            # Get description from docstring
            description = self._get_function_description(view_function)

            return RouteInfo(
                endpoint=endpoint,
                rule=rule.rule,
                methods=methods,
                blueprint=blueprint,
                view_function=view_name,
                module=module,
                parameters=parameters,
                auth_required=auth_required,
                roles_required=roles_required,
                description=description,
                file_path=file_path,
                line_number=line_number
            )

        except Exception as e:
            print(f"⚠️  Error analyzing route {rule.endpoint}: {e}")
            return None

    def _extract_parameters(self, rule_string: str) -> List[str]:
        """Extract parameter names from route rule"""
        # Find all parameters in angle brackets
        parameters = re.findall(r'<([^>]+)>', rule_string)

        # Clean up parameter names (remove type hints)
        clean_params = []
        for param in parameters:
            if ':' in param:
                # Remove type hint (e.g., 'int:id' -> 'id')
                param = param.split(':', 1)[1]
            clean_params.append(param)

        return clean_params

    def _get_function_location(self, func) -> tuple[Optional[str], Optional[int]]:
        """Get file path and line number of function definition"""
        try:
            if func:
                file_path = inspect.getfile(func)
                line_number = inspect.getsourcelines(func)[1]
                # Make path relative to project root
                project_root = os.path.dirname(os.path.dirname(__file__))
                rel_path = os.path.relpath(file_path, project_root)
                return rel_path, line_number
        except (OSError, TypeError):
            pass
        return None, None

    def _analyze_auth_requirements(self, func) -> tuple[bool, List[str]]:
        """Analyze authentication and authorization requirements"""
        auth_required = False
        roles_required = []

        if not func:
            return auth_required, roles_required

        try:
            # Check for common authentication decorators
            if hasattr(func, '__wrapped__'):
                # Look for wrapped function (decorated)
                wrapper = func
                while hasattr(wrapper, '__wrapped__'):
                    wrapper_name = getattr(wrapper, '__name__', '')
                    if any(auth_keyword in wrapper_name.lower() for auth_keyword in
                           ['login_required', 'auth_required', 'authenticated', 'protected']):
                        auth_required = True
                    wrapper = wrapper.__wrapped__

            # Check source code for authentication patterns
            try:
                source = inspect.getsource(func)
                if any(pattern in source for pattern in [
                    'login_required', 'auth_required', 'current_user',
                    'session.get', 'g.user', '@login_required'
                ]):
                    auth_required = True

                # Look for role-based patterns
                role_patterns = re.findall(r'role[s]?\s*[=:]\s*[\'"]([^\'"]+)[\'"]', source, re.IGNORECASE)
                roles_required.extend(role_patterns)

            except (OSError, TypeError):
                pass

        except Exception:
            pass

        return auth_required, roles_required

    def _get_function_description(self, func) -> Optional[str]:
        """Get function description from docstring"""
        try:
            if func and func.__doc__:
                # Get first line of docstring
                return func.__doc__.strip().split('\n')[0]
        except Exception:
            pass
        return None

    def categorize_by_blueprint(self) -> Dict[str, List[RouteInfo]]:
        """Categorize routes by blueprint"""
        print("📂 Categorizing routes by blueprint...")

        self.blueprint_routes = {}

        for route in self.routes.values():
            blueprint = route.blueprint or 'main'
            if blueprint not in self.blueprint_routes:
                self.blueprint_routes[blueprint] = []
            self.blueprint_routes[blueprint].append(route)

        # Sort routes within each blueprint
        for blueprint in self.blueprint_routes:
            self.blueprint_routes[blueprint].sort(key=lambda r: r.endpoint)

        print(f"✅ Categorized routes into {len(self.blueprint_routes)} blueprints")
        return self.blueprint_routes

    def generate_route_mapping(self) -> Dict[str, Any]:
        """Generate comprehensive route mapping"""
        print("📋 Generating route mapping...")

        mapping = {
            'metadata': {
                'total_routes': len(self.routes),
                'blueprints': list(self.blueprint_routes.keys()),
                'generated_at': self._get_timestamp()
            },
            'routes': {},
            'blueprints': {}
        }

        # Add individual routes
        for endpoint, route in self.routes.items():
            mapping['routes'][endpoint] = asdict(route)

        # Add blueprint summaries
        for blueprint, routes in self.blueprint_routes.items():
            mapping['blueprints'][blueprint] = {
                'route_count': len(routes),
                'endpoints': [r.endpoint for r in routes],
                'auth_required_count': sum(1 for r in routes if r.auth_required),
                'methods_used': list(set(method for r in routes for method in r.methods))
            }

        return mapping

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


class RouteReporter:
    """Generate reports from route discovery results"""

    def __init__(self, route_mapping: Dict[str, Any]):
        self.mapping = route_mapping

    def save_json(self, output_path: str):
        """Save route mapping as JSON"""
        print(f"💾 Saving JSON report to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, indent=2, ensure_ascii=False)

    def save_yaml(self, output_path: str):
        """Save route mapping as YAML"""
        print(f"💾 Saving YAML report to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.mapping, f, default_flow_style=False, allow_unicode=True)

    def save_csv(self, output_path: str):
        """Save route mapping as CSV"""
        print(f"💾 Saving CSV report to {output_path}")

        fieldnames = [
            'endpoint', 'rule', 'methods', 'blueprint', 'view_function',
            'module', 'parameters', 'auth_required', 'roles_required',
            'description', 'file_path', 'line_number'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for route_data in self.mapping['routes'].values():
                # Convert lists to strings for CSV
                route_data['methods'] = ', '.join(route_data['methods'])
                route_data['parameters'] = ', '.join(route_data['parameters'])
                route_data['roles_required'] = ', '.join(route_data['roles_required'])
                writer.writerow(route_data)

    def print_summary(self):
        """Print summary of discovered routes"""
        metadata = self.mapping['metadata']
        blueprints = self.mapping['blueprints']

        print("\n" + "=" * 60)
        print("📊 ROUTE DISCOVERY SUMMARY")
        print("=" * 60)
        print(f"Total Routes: {metadata['total_routes']}")
        print(f"Blueprints: {len(metadata['blueprints'])}")
        print(f"Generated: {metadata['generated_at']}")

        print("\n📂 Blueprint Breakdown:")
        for blueprint, info in blueprints.items():
            auth_count = info['auth_required_count']
            total_count = info['route_count']
            print(f"  {blueprint:20} {total_count:3d} routes ({auth_count} protected)")

        print("\n🔒 Authentication Summary:")
        total_protected = sum(info['auth_required_count'] for info in blueprints.values())
        total_public = metadata['total_routes'] - total_protected
        print(f"  Protected routes: {total_protected}")
        print(f"  Public routes: {total_public}")

        print("\n🌐 HTTP Methods Used:")
        all_methods = set()
        for info in blueprints.values():
            all_methods.update(info['methods_used'])
        for method in sorted(all_methods):
            print(f"  {method}")


def main():
    """Main function to run route discovery"""
    import argparse

    parser = argparse.ArgumentParser(description='Discover and catalog Flask routes')
    parser.add_argument('--output', '-o', default='route_mapping.json',
                        help='Output file path (default: route_mapping.json)')
    parser.add_argument('--format', '-f', choices=['json', 'yaml', 'csv'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--summary', '-s', action='store_true',
                        help='Print summary to console')

    args = parser.parse_args()

    try:
        print("🚀 Starting Route Discovery for JobFinders")
        print("-" * 50)

        # Create Flask app
        print("🏗️  Creating Flask application...")
        config = config_instance()
        app = create_app(config)

        with app.app_context():
            # Discover routes
            engine = RouteDiscoveryEngine(app)
            routes = engine.discover_routes()
            blueprint_routes = engine.categorize_by_blueprint()
            route_mapping = engine.generate_route_mapping()

            # Generate report
            reporter = RouteReporter(route_mapping)

            # Save output
            if args.format == 'json':
                reporter.save_json(args.output)
            elif args.format == 'yaml':
                reporter.save_yaml(args.output)
            elif args.format == 'csv':
                reporter.save_csv(args.output)

            # Print summary if requested
            if args.summary:
                reporter.print_summary()

            print(f"\n✅ Route discovery completed successfully!")
            print(f"📄 Report saved to: {args.output}")

    except Exception as e:
        print(f"❌ Error during route discovery: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
