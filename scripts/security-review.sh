#!/bin/bash

# Security Review Script for ClawChat
# This script checks for common security issues before public release

set -e

echo "🔒 Running ClawChat Security Review"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        if [ "$3" = "fail" ]; then
            exit 1
        fi
    fi
}

# Check 1: No hardcoded secrets
echo -e "\n1. Checking for hardcoded secrets..."
SECRETS_FOUND=0
SECRETS_FOUND=$(grep -r -E "(password|secret|key|token|auth)\s*[=:]\s*['\"][^'\"]{8,}['\"]" \
    --include="*.py" --include="*.js" --include="*.json" --include="*.yaml" --include="*.yml" \
    . 2>/dev/null | grep -v "test_" | grep -v "example" | grep -v "dummy" | wc -l)

if [ $SECRETS_FOUND -eq 0 ]; then
    print_status 0 "No hardcoded secrets found"
else
    print_status 1 "Found $SECRETS_FOUND potential hardcoded secrets" "fail"
    grep -r -E "(password|secret|key|token|auth)\s*[=:]\s*['\"][^'\"]{8,}['\"]" \
        --include="*.py" --include="*.js" --include="*.json" --include="*.yaml" --include="*.yml" \
        . 2>/dev/null | grep -v "test_" | grep -v "example" | grep -v "dummy"
fi

# Check 2: No API keys in code
echo -e "\n2. Checking for API keys..."
API_KEYS_FOUND=$(grep -r -i -E "(api[_-]?key|api[_-]?token|access[_-]?token|refresh[_-]?token|client[_-]?secret)" \
    --include="*.py" --include="*.js" --include="*.json" . 2>/dev/null | wc -l)

if [ $API_KEYS_FOUND -eq 0 ]; then
    print_status 0 "No API keys found in code"
else
    print_status 1 "Found $API_KEYS_FOUND potential API keys" "warn"
    grep -r -i -E "(api[_-]?key|api[_-]?token|access[_-]?token|refresh[_-]?token|client[_-]?secret)" \
        --include="*.py" --include="*.js" --include="*.json" . 2>/dev/null
fi

# Check 3: File permissions
echo -e "\n3. Checking file permissions..."
BAD_PERMS=0
# Check for world-writable files
BAD_PERMS=$(find . -type f -perm /o=w ! -path "./.git/*" ! -name "*.sh" 2>/dev/null | wc -l)

if [ $BAD_PERMS -eq 0 ]; then
    print_status 0 "No world-writable files found"
else
    print_status 1 "Found $BAD_PERMS world-writable files" "warn"
    find . -type f -perm /o=w ! -path "./.git/*" ! -name "*.sh" 2>/dev/null
fi

# Check 4: Shell script safety
echo -e "\n4. Checking shell script safety..."
for script in $(find . -name "*.sh" -type f); do
    if head -1 "$script" | grep -q "#!/bin/bash"; then
        if grep -q "set -e" "$script"; then
            print_status 0 "Script $script has safety features"
        else
            print_status 1 "Script $script missing 'set -e'" "warn"
        fi
    fi
done

# Check 5: Python security issues
echo -e "\n5. Checking Python security patterns..."
# Check for eval() usage
EVAL_FOUND=$(grep -r "eval(" --include="*.py" . 2>/dev/null | wc -l)
if [ $EVAL_FOUND -eq 0 ]; then
    print_status 0 "No eval() usage found"
else
    print_status 1 "Found $EVAL_FOUND uses of eval()" "warn"
    grep -r "eval(" --include="*.py" . 2>/dev/null
fi

# Check 6: Dependency security
echo -e "\n6. Checking dependency security..."
if [ -f "backend/requirements.txt" ]; then
    print_status 0 "Requirements file found"
    # Check for known vulnerable packages (simplified check)
    if grep -q "requests" backend/requirements.txt; then
        print_status 0 "Requests library found (common HTTP library)"
    fi
else
    print_status 1 "No requirements.txt found" "warn"
fi

# Check 7: Configuration files
echo -e "\n7. Checking configuration files..."
if [ -f "config.yaml" ] || [ -f "config.yml" ] || [ -f ".env.example" ]; then
    print_status 0 "Configuration templates found"
    
    # Check if real config files are gitignored
    if grep -q "config.yaml" .gitignore 2>/dev/null || \
       grep -q "config.yml" .gitignore 2>/dev/null || \
       grep -q ".env" .gitignore 2>/dev/null; then
        print_status 0 "Config files are in .gitignore"
    else
        print_status 1 "Config files may not be gitignored" "warn"
    fi
else
    print_status 1 "No configuration templates found" "warn"
fi

# Check 8: SSL/TLS configuration
echo -e "\n8. Checking SSL/TLS references..."
SSL_FOUND=$(grep -r -i "ssl\|tls\|https" --include="*.py" --include="*.js" . 2>/dev/null | wc -l)
if [ $SSL_FOUND -gt 0 ]; then
    print_status 0 "SSL/TLS references found (good for security)"
else
    print_status 1 "No SSL/TLS references found" "warn"
fi

# Check 9: Input validation
echo -e "\n9. Checking for input validation patterns..."
VALIDATION_FOUND=$(grep -r -i "validate\|sanitize\|escape\|filter" --include="*.py" . 2>/dev/null | wc -l)
if [ $VALIDATION_FOUND -gt 10 ]; then
    print_status 0 "Input validation patterns found"
else
    print_status 1 "Limited input validation patterns found" "warn"
fi

# Check 10: Security headers in frontend
echo -e "\n10. Checking frontend security..."
if [ -f "frontend/index.html" ]; then
    if grep -q "Content-Security-Policy" frontend/index.html 2>/dev/null || \
       grep -q "X-Content-Type-Options" frontend/index.html 2>/dev/null; then
        print_status 0 "Security headers found in HTML"
    else
        print_status 1 "No security headers in HTML" "warn"
    fi
else
    print_status 0 "No frontend HTML to check"
fi

# Summary
echo -e "\n${GREEN}===================================${NC}"
echo -e "${GREEN}Security Review Complete${NC}"
echo -e "${GREEN}===================================${NC}"
echo ""
echo "Recommendations:"
echo "1. Run 'safety check' for Python dependency vulnerabilities"
echo "2. Run 'bandit -r backend/' for Python security scanning"
echo "3. Consider adding a Content Security Policy to frontend"
echo "4. Ensure all secrets are in environment variables"
echo "5. Regular security updates for dependencies"
echo ""
echo "For production deployment, also consider:"
echo "- Web Application Firewall (WAF)"
echo "- DDoS protection"
echo "- Regular security audits"
echo "- Incident response plan"

exit 0