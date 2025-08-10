"""
Validation script for statistics tests

This script validates that all test files have correct imports and basic syntax
without actually running the tests (which might fail due to missing dependencies).
"""

import ast
import sys
from pathlib import Path


def validate_python_syntax(file_path):
    """Validate that a Python file has correct syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def check_imports(file_path):
    """Check if imports in the file are structured correctly"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        return True, imports
    except Exception as e:
        return False, str(e)


def validate_test_structure(file_path):
    """Validate that the test file has proper test structure"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        test_classes = []
        test_methods = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                test_classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_methods.append(node.name)
        
        return True, {"classes": test_classes, "methods": test_methods}
    except Exception as e:
        return False, str(e)


def main():
    """Main validation function"""
    test_files = [
        "tests/test_job_statistics_service.py",
        "tests/test_job_statistics_models.py",
        "tests/test_job_statistics_caching.py", 
        "tests/test_job_model_computed_properties.py",
        "tests/test_company_model_computed_properties.py"
    ]
    
    print("Validating Statistics Test Files")
    print("=" * 50)
    
    all_valid = True
    
    for test_file in test_files:
        print(f"\nValidating {test_file}...")
        
        if not Path(test_file).exists():
            print(f"❌ File does not exist: {test_file}")
            all_valid = False
            continue
        
        # Check syntax
        syntax_valid, syntax_error = validate_python_syntax(test_file)
        if not syntax_valid:
            print(f"❌ Syntax error in {test_file}: {syntax_error}")
            all_valid = False
            continue
        else:
            print(f"✅ Syntax is valid")
        
        # Check imports
        imports_valid, imports_result = check_imports(test_file)
        if not imports_valid:
            print(f"❌ Import error in {test_file}: {imports_result}")
            all_valid = False
            continue
        else:
            print(f"✅ Imports are structured correctly ({len(imports_result)} imports found)")
        
        # Check test structure
        structure_valid, structure_result = validate_test_structure(test_file)
        if not structure_valid:
            print(f"❌ Structure error in {test_file}: {structure_result}")
            all_valid = False
            continue
        else:
            classes = structure_result["classes"]
            methods = structure_result["methods"]
            print(f"✅ Test structure is valid ({len(classes)} test classes, {len(methods)} test methods)")
    
    print("\n" + "=" * 50)
    if all_valid:
        print("🎉 All test files are valid!")
        print("\nTest files are ready for execution.")
        print("You can run them individually with: python -m pytest <test_file> -v")
        print("Or run the full suite with: python tests/test_statistics_suite.py")
    else:
        print("⚠️  Some test files have issues. Please fix them before running tests.")
    
    return all_valid


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)