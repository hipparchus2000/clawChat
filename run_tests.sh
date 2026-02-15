#!/bin/bash
#
# ClawChat Test Runner Script
# ============================
#
# This script runs the ClawChat WebSocket server and client test suite
# with coverage reporting. It supports multiple test modes and generates
# detailed coverage reports.
#
# Usage:
#   ./run_tests.sh                   Run all tests with coverage
#   ./run_tests.sh unit              Run only unit tests
#   ./run_tests.sh integration       Run only integration tests
#   ./run_tests.sh quick             Run quick tests (no coverage)
#   ./run_tests.sh verbose           Run with verbose output
#   ./run_tests.sh ci                Run in CI mode (strict)
#   ./run_tests.sh phase2            Run Phase 2 tests (file ops, chat, PWA)
#   ./run_tests.sh security          Run security tests only
#   ./run_tests.sh performance       Run performance tests only
#
# Exit codes:
#   0 - All tests passed
#   1 - Tests failed
#   2 - Invalid arguments
#   3 - Missing dependencies
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${SCRIPT_DIR}/tests"
COVERAGE_DIR="${SCRIPT_DIR}/htmlcov"

# Default settings
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_PHASE2=true
RUN_SECURITY=false
RUN_PERFORMANCE=false
VERBOSE=false
COVERAGE=true
CI_MODE=false
FAIL_FAST=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        unit)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_PHASE2=false
            ;;
        integration)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            RUN_PHASE2=false
            ;;
        phase2)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_PHASE2=true
            ;;
        security)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_PHASE2=false
            RUN_SECURITY=true
            ;;
        performance)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_PHASE2=false
            RUN_PERFORMANCE=true
            ;;
        quick)
            COVERAGE=false
            ;;
        verbose|-v)
            VERBOSE=true
            ;;
        ci)
            CI_MODE=true
            FAIL_FAST=true
            ;;
        ff|--failfast)
            FAIL_FAST=true
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            echo "Usage: $0 [unit|integration|phase2|security|performance|quick|verbose|ci]"
            exit 2
            ;;
    esac
done

# Print banner
echo -e "${BLUE}${BOLD}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ClawChat Test Runner                          ║"
echo "║    WebSocket, File API, Chat & PWA Test Suite              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Python version: $PYTHON_VERSION"

# Check for required dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

MISSING_DEPS=()

if ! python3 -c "import pytest" 2>/dev/null; then
    MISSING_DEPS+=("pytest")
fi

if ! python3 -c "import pytest_asyncio" 2>/dev/null; then
    MISSING_DEPS+=("pytest-asyncio")
fi

if $COVERAGE && ! python3 -c "import pytest_cov" 2>/dev/null; then
    MISSING_DEPS+=("pytest-cov")
fi

if ! python3 -c "import websockets" 2>/dev/null; then
    MISSING_DEPS+=("websockets")
fi

if ! python3 -c "import yaml" 2>/dev/null; then
    MISSING_DEPS+=("pyyaml")
fi

if ! python3 -c "import aiofiles" 2>/dev/null; then
    MISSING_DEPS+=("aiofiles")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${RED}Missing required dependencies:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo -e "${YELLOW}Install with: pip install ${MISSING_DEPS[*]}${NC}"
    exit 3
fi

echo -e "${GREEN}  All dependencies installed ✓${NC}"

# Create coverage directory
if $COVERAGE; then
    mkdir -p "$COVERAGE_DIR"
fi

# Build pytest arguments
PYTEST_ARGS=()

if $VERBOSE; then
    PYTEST_ARGS+=("-v" "-s")
else
    PYTEST_ARGS+=("-v")
fi

if $FAIL_FAST; then
    PYTEST_ARGS+=("-x")
fi

if $CI_MODE; then
    PYTEST_ARGS+=("--tb=short")
else
    PYTEST_ARGS+=("--tb=long")
fi

# Add coverage arguments
if $COVERAGE; then
    PYTEST_ARGS+=(
        "--cov=backend"
        "--cov=tests"
        "--cov-report=term-missing"
        "--cov-report=html:${COVERAGE_DIR}"
        "--cov-report=xml:${SCRIPT_DIR}/coverage.xml"
        "--cov-branch"
    )
    
    if $CI_MODE; then
        PYTEST_ARGS+=("--cov-fail-under=80")
    fi
fi

# Set test files based on options
TEST_FILES=()

if $RUN_UNIT; then
    TEST_FILES+=("${TEST_DIR}/test_websocket.py")
fi

if $RUN_INTEGRATION; then
    TEST_FILES+=("${TEST_DIR}/test_integration.py")
fi

if $RUN_PHASE2; then
    TEST_FILES+=(
        "${TEST_DIR}/test_file_operations.py"
        "${TEST_DIR}/test_chat.py"
        "${TEST_DIR}/test_pwa.py"
    )
fi

if $RUN_SECURITY; then
    PYTEST_ARGS+=("-k" "security or traversal or permission")
    TEST_FILES+=(
        "${TEST_DIR}/test_file_operations.py"
    )
fi

if $RUN_PERFORMANCE; then
    PYTEST_ARGS+=("-m" "performance")
    TEST_FILES+=(
        "${TEST_DIR}/test_file_operations.py"
        "${TEST_DIR}/test_chat.py"
        "${TEST_DIR}/test_pwa.py"
    )
fi

echo ""
echo -e "${BOLD}Test Configuration:${NC}"
echo "  Unit tests:       $RUN_UNIT"
echo "  Integration:      $RUN_INTEGRATION"
echo "  Phase 2:          $RUN_PHASE2"
echo "  Security:         $RUN_SECURITY"
echo "  Performance:      $RUN_PERFORMANCE"
echo "  Coverage:         $COVERAGE"
echo "  Verbose:          $VERBOSE"
echo "  CI Mode:          $CI_MODE"
echo "  Test directory:   $TEST_DIR"
if $COVERAGE; then
    echo "  Coverage dir:     $COVERAGE_DIR"
fi
echo ""

# Track results
OVERALL_STATUS=0

# Function to run tests with reporting
run_test_file() {
    local test_file=$1
    local test_name=$2
    local extra_args=$3
    
    echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}  Running $test_name${NC}"
    echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local ARGS=("${PYTEST_ARGS[@]}")
    if [ -n "$extra_args" ]; then
        ARGS+=("$extra_args")
    fi
    
    if python3 -m pytest "$test_file" "${ARGS[@]}"; then
        echo ""
        echo -e "${GREEN}${BOLD}✓ $test_name passed${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}${BOLD}✗ $test_name failed${NC}"
        return 1
    fi
}

# Run tests
for test_file in "${TEST_FILES[@]}"; do
    if [ -f "$test_file" ]; then
        filename=$(basename "$test_file" .py)
        
        case $filename in
            test_websocket)
                run_test_file "$test_file" "Unit Tests (WebSocket)" || OVERALL_STATUS=1
                ;;
            test_integration)
                run_test_file "$test_file" "Integration Tests" "--timeout=60" || OVERALL_STATUS=1
                ;;
            test_file_operations)
                run_test_file "$test_file" "Phase 2: File Operations" || OVERALL_STATUS=1
                ;;
            test_chat)
                run_test_file "$test_file" "Phase 2: Chat Functionality" || OVERALL_STATUS=1
                ;;
            test_pwa)
                run_test_file "$test_file" "Phase 2: PWA Features" || OVERALL_STATUS=1
                ;;
        esac
    else
        echo -e "${YELLOW}Warning: Test file not found: $test_file${NC}"
    fi
    
    if [ $OVERALL_STATUS -ne 0 ] && $FAIL_FAST; then
        break
    fi
done

# Print coverage report location
if $COVERAGE && [ $OVERALL_STATUS -eq 0 ]; then
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  Coverage Reports${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  HTML Report: ${COVERAGE_DIR}/index.html"
    echo "  XML Report:  ${SCRIPT_DIR}/coverage.xml"
    echo ""
    
    # Try to open HTML report on macOS/Linux desktop
    if [ -f "${COVERAGE_DIR}/index.html" ] && [ -z "$CI" ]; then
        if command -v open &> /dev/null; then
            echo "  Opening HTML report..."
            open "${COVERAGE_DIR}/index.html" 2>/dev/null || true
        elif command -v xdg-open &> /dev/null; then
            echo "  Opening HTML report..."
            xdg-open "${COVERAGE_DIR}/index.html" 2>/dev/null || true
        fi
    fi
fi

# Print summary
echo ""
echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}${BOLD}  Test Summary${NC}"
echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║              ALL TESTS PASSED!                            ║${NC}"
    echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}${BOLD}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║              SOME TESTS FAILED                            ║${NC}"
    echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════╝${NC}"
fi

echo ""

exit $OVERALL_STATUS
