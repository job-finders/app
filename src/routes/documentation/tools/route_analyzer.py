#!/usr/bin/env python3
"""
Route Analysis Tool for Job Finders Platform

This tool analyzes route files to extract metadata, decorators, and function signatures
for generating comprehensive route documentation.
"""

import os
import ast
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import importlib.util


class RouteAnalyzer:
    """Analyzes Flask route files to extract documentation metadata."""

    def __init__(self, routes_dir: str = "src/routes"):
        self.routes_dir = Path(routes_dir)
        self.route_data = {}

    def analyze_all_routes(self) -> Dict[str, Any]:
        """Analyze all route files in the routes directory."""
        route_files = self._find_route_files()

        for route_file in route_files:
            try:
                route_info = self._analyze_route_file(route_file)
                if route_info:
                    category = self._get_route_category(route_file)
                    if category not in self.route_data:
                        self.route_data[category] = []
                    self.route_data[category].extend(route_info)
            except Exception as e:
                print(f"Error analyzing {route_file}: {e}")

        return self.route_data

    def _find_route_files(self) -> List[Path]:
        """Find all Python route files."""
        route_files = []

        for root, dirs, files in os.walk(self.routes_dir):
            # Skip documentation and __pycache__ directories
            dirs[:] = [d for d in dirs if d not in ['documentation', '__pycache__']]

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    route_files.append(Path(root) / file)

        return route_files

    def _get_route_category(self, route_file: Path) -> str:
        """Extract route category from file path."""
        parts = route_file.parts
        if 'routes' in parts:
            routes_index = parts.index('routes')
            if routes_index + 1 < len(parts):
                category = parts[routes_index + 1]
                # Remove '_routes' suffix if present
                if category.endswith('_routes'):
                    category = category[:-7]
                return category
        return 'misc'

    def _analyze_route_file(self, route_file: Path) -> List[Dict[str, Any]]:
        """Analyze a single route file."""
        try:
            with open(route_file, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            routes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    route_info = self._extract_route_info(node, content)
                    if route_info:
                        route_info['file_path'] = str(route_file)
                        routes.append(route_info)

            return routes

        except Exception as e:
            print(f"Error parsing {route_file}: {e}")
            return []

    def _extract_route_info(self, func_node: ast.FunctionDef, content: str) -> Optional[Dict[str, Any]]:
        """Extract route information from a function node."""
        route_info = {
            'function_name': func_node.name,
            'line_number': func_node.lineno,
            'decorators': [],
            'parameters': [],
            'docstring': ast.get_docstring(func_node),
            'http_methods': [],
            'url_patterns': [],
            'blueprint': None,
            'authentication_required': False,
            'rate_limited': False,
            'template_calls': [],
            'controller_calls': []
        }

        # Extract decorators
        for decorator in func_node.decorator_list:
            decorator_info = self._parse_decorator(decorator)
            if decorator_info:
                route_info['decorators'].append(decorator_info)

                # Extract route-specific information
                if decorator_info['name'] in ['route', 'get', 'post', 'put', 'delete', 'patch']:
                    if 'args' in decorator_info and decorator_info['args']:
                        route_info['url_patterns'].append(decorator_info['args'][0])

                    if 'methods' in decorator_info.get('kwargs', {}):
                        methods = decorator_info['kwargs']['methods']
                        if isinstance(methods, list):
                            route_info['http_methods'].extend(methods)
                        else:
                            route_info['http_methods'].append(methods)

                # Check for authentication decorators
                if decorator_info['name'] in ['login_required', 'jwt_required', 'auth_required']:
                    route_info['authentication_required'] = True

                # Check for rate limiting
                if 'rate_limit' in decorator_info['name'].lower():
                    route_info['rate_limited'] = True

        # Extract function parameters
        for arg in func_node.args.args:
            if arg.arg != 'self':  # Skip self parameter
                route_info['parameters'].append({
                    'name': arg.arg,
                    'annotation': ast.unparse(arg.annotation) if arg.annotation else None
                })

        # Extract template and controller calls from function body
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_info = self._parse_function_call(node)
                if call_info:
                    if 'render_template' in call_info['function']:
                        route_info['template_calls'].append(call_info)
                    elif 'controller' in call_info['function'].lower():
                        route_info['controller_calls'].append(call_info)

        # Only return if this appears to be a route function
        if route_info['url_patterns'] or any(d['name'] in ['route', 'get', 'post', 'put', 'delete', 'patch']
                                             for d in route_info['decorators']):
            return route_info

        return None

    def _parse_decorator(self, decorator: ast.AST) -> Optional[Dict[str, Any]]:
        """Parse a decorator to extract its information."""
        try:
            if isinstance(decorator, ast.Name):
                return {'name': decorator.id, 'args': [], 'kwargs': {}}

            elif isinstance(decorator, ast.Call):
                decorator_info = {
                    'name': ast.unparse(decorator.func),
                    'args': [],
                    'kwargs': {}
                }

                # Extract positional arguments
                for arg in decorator.args:
                    try:
                        if isinstance(arg, ast.Constant):
                            decorator_info['args'].append(arg.value)
                        else:
                            decorator_info['args'].append(ast.unparse(arg))
                    except:
                        decorator_info['args'].append('<unparseable>')

                # Extract keyword arguments
                for keyword in decorator.keywords:
                    try:
                        if isinstance(keyword.value, ast.Constant):
                            decorator_info['kwargs'][keyword.arg] = keyword.value.value
                        else:
                            decorator_info['kwargs'][keyword.arg] = ast.unparse(keyword.value)
                    except:
                        decorator_info['kwargs'][keyword.arg] = '<unparseable>'

                return decorator_info

            elif isinstance(decorator, ast.Attribute):
                return {'name': ast.unparse(decorator), 'args': [], 'kwargs': {}}

        except Exception as e:
            print(f"Error parsing decorator: {e}")

        return None

    def _parse_function_call(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        """Parse a function call to extract relevant information."""
        try:
            call_info = {
                'function': ast.unparse(call_node.func),
                'args': [],
                'kwargs': {}
            }

            # Extract arguments
            for arg in call_node.args:
                try:
                    if isinstance(arg, ast.Constant):
                        call_info['args'].append(arg.value)
                    else:
                        call_info['args'].append(ast.unparse(arg))
                except:
                    call_info['args'].append('<unparseable>')

            # Extract keyword arguments
            for keyword in call_node.keywords:
                try:
                    if isinstance(keyword.value, ast.Constant):
                        call_info['kwargs'][keyword.arg] = keyword.value.value
                    else:
                        call_info['kwargs'][keyword.arg] = ast.unparse(keyword.value)
                except:
                    call_info['kwargs'][keyword.arg] = '<unparseable>'

            return call_info

        except Exception as e:
            print(f"Error parsing function call: {e}")

        return None

    def generate_documentation_data(self, output_file: str = "route_analysis.json"):
        """Generate and save route analysis data."""
        data = self.analyze_all_routes()

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Route analysis saved to {output_file}")
        return data

    def print_summary(self):
        """Print a summary of analyzed routes."""
        if not self.route_data:
            self.analyze_all_routes()

        print("Route Analysis Summary")
        print("=" * 50)

        total_routes = 0
        for category, routes in self.route_data.items():
            route_count = len(routes)
            total_routes += route_count
            print(f"{category}: {route_count} routes")

            # Show authentication stats
            auth_required = sum(1 for r in routes if r['authentication_required'])
            rate_limited = sum(1 for r in routes if r['rate_limited'])

            if auth_required > 0:
                print(f"  - {auth_required} require authentication")
            if rate_limited > 0:
                print(f"  - {rate_limited} have rate limiting")

        print(f"\nTotal routes analyzed: {total_routes}")


def main():
    """Main function to run route analysis."""
    analyzer = RouteAnalyzer()

    print("Analyzing Job Finders routes...")
    data = analyzer.generate_documentation_data()
    analyzer.print_summary()

    return data


if __name__ == "__main__":
    main()
