#!/usr/bin/env python3
"""
Test runner for the AI Debate Agents project.
Provides multiple test execution options with different levels of complexity.
"""
import subprocess
import sys
import os
import argparse


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"\nExit code: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def run_simple_tests():
    """Run only simple tests that avoid complex imports."""
    cmd = ["python", "-m", "pytest", "-m", "simple", "-v", "--tb=short"]
    return run_command(cmd, "Simple Tests (no complex imports)")


def run_basic_tests():
    """Run basic functionality tests only."""
    cmd = ["python", "-m", "pytest", "tests/test_basic_functionality.py", "tests/test_simple_api.py", "-v"]
    return run_command(cmd, "Basic Functionality Tests")


def run_unit_tests():
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "-m", "unit", "-v", "--tb=short"]
    return run_command(cmd, "Unit Tests")


def run_integration_tests():
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "-m", "integration", "-v", "--tb=short"]
    return run_command(cmd, "Integration Tests")


def run_all_tests():
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
    return run_command(cmd, "All Tests")


def run_coverage_report():
    """Run tests with coverage report."""
    cmd = ["python", "-m", "pytest", "--cov=.", "--cov-report=html", "--cov-report=term", "-v"]
    return run_command(cmd, "Coverage Report")


def run_quick_test():
    """Run a quick subset of tests."""
    cmd = ["python", "-m", "pytest", "-m", "fast", "-v", "--tb=line", "-x"]
    return run_command(cmd, "Quick Test (fast tests only)")


def run_specific_test_file():
    """Run a specific test file."""
    print("\nAvailable test files:")
    test_files = []
    if os.path.exists("tests"):
        for file in os.listdir("tests"):
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(file)
                print(f"  {len(test_files)}. {file}")
    
    if not test_files:
        print("No test files found!")
        return False
    
    try:
        choice = int(input(f"\nSelect test file (1-{len(test_files)}): "))
        if 1 <= choice <= len(test_files):
            selected_file = test_files[choice - 1]
            cmd = ["python", "-m", "pytest", f"tests/{selected_file}", "-v"]
            return run_command(cmd, f"Test file: {selected_file}")
        else:
            print("Invalid choice!")
            return False
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Test runner for AI Debate Agents")
    parser.add_argument("--simple", action="store_true", help="Run simple tests only")
    parser.add_argument("--basic", action="store_true", help="Run basic functionality tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--quick", action="store_true", help="Run quick tests")
    parser.add_argument("--file", action="store_true", help="Run specific test file")
    
    args = parser.parse_args()
    
    # If any argument is provided, run that test type
    if args.simple:
        return run_simple_tests()
    elif args.basic:
        return run_basic_tests()
    elif args.unit:
        return run_unit_tests()
    elif args.integration:
        return run_integration_tests()
    elif args.all:
        return run_all_tests()
    elif args.coverage:
        return run_coverage_report()
    elif args.quick:
        return run_quick_test()
    elif args.file:
        return run_specific_test_file()
    
    # If no arguments provided, show interactive menu
    print("AI Debate Agents - Test Runner")
    print("=" * 40)
    print("1. Simple Tests (recommended - no complex imports)")
    print("2. Basic Functionality Tests")
    print("3. Unit Tests")
    print("4. Quick Tests (fast tests only)")
    print("5. Integration Tests")
    print("6. All Tests")
    print("7. Coverage Report")
    print("8. Run Specific Test File")
    print("9. Exit")
    
    try:
        choice = input("\nSelect an option (1-9): ").strip()
        
        if choice == '1':
            success = run_simple_tests()
        elif choice == '2':
            success = run_basic_tests()
        elif choice == '3':
            success = run_unit_tests()
        elif choice == '4':
            success = run_quick_test()
        elif choice == '5':
            success = run_integration_tests()
        elif choice == '6':
            success = run_all_tests()
        elif choice == '7':
            success = run_coverage_report()
        elif choice == '8':
            success = run_specific_test_file()
        elif choice == '9':
            print("Exiting...")
            return True
        else:
            print("Invalid choice!")
            return False
        
        if success:
            print(f"\n✅ Tests completed successfully!")
        else:
            print(f"\n❌ Tests failed!")
        
        return success
        
    except KeyboardInterrupt:
        print("\n\nTest execution cancelled by user.")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 