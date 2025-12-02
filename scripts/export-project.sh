#!/bin/bash
# Export project from monorepo to separate repository
# Usage: ./export-project.sh <project-name> <target-repo-url>

set -e

PROJECT_NAME=$1
TARGET_REPO=$2

if [ -z "$PROJECT_NAME" ] || [ -z "$TARGET_REPO" ]; then
  echo "❌ Usage: $0 <project-name> <target-repo-url>"
  echo ""
  echo "Example:"
  echo "  $0 user-analytics https://github.com/company/user-analytics.git"
  exit 1
fi

PROJECTS_DIR="$(cd "$(dirname "$0")/../data-platform/projects" && pwd)"
PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"

echo "📦 Exporting project: $PROJECT_NAME"
echo "🎯 Target repository: $TARGET_REPO"
echo ""

# Validate project exists
if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ Project not found: $PROJECT_DIR"
  echo ""
  echo "Available projects:"
  ls -1 "$PROJECTS_DIR" | grep -v "^_" | sed 's/^/  - /'
  exit 1
fi

# Validate PROJECT.yaml
if [ ! -f "$PROJECT_DIR/PROJECT.yaml" ]; then
  echo "❌ Invalid project: missing PROJECT.yaml"
  exit 1
fi

# Parse project metadata
PROJECT_VERSION=$(grep "^version:" "$PROJECT_DIR/PROJECT.yaml" | cut -d'"' -f2 | xargs)
echo "🔖 Project version: $PROJECT_VERSION"
echo ""

# Create temporary directory for export
TEMP_DIR=$(mktemp -d)
EXPORT_DIR="$TEMP_DIR/$PROJECT_NAME"

echo "📁 Preparing export in: $TEMP_DIR"

# Copy project files
cp -r "$PROJECT_DIR" "$EXPORT_DIR"

# Create standalone repository structure
cd "$TEMP_DIR"

# Initialize git
git init

# Create README at root
cat > README.md <<EOF
# $PROJECT_NAME

Exported from datacluster monorepo.

## Setup

\`\`\`bash
# Install dependencies
pip install -r requirements.txt

# Or with poetry
poetry install

# Run tests
pytest tests/

# Deploy
kubectl apply -k k8s/overlays/prod/
\`\`\`

## Documentation

See [\`docs/\`](./docs/) for complete documentation.

## Original Repository

This project was exported from: https://github.com/bayleafwalker/datacluster
EOF

# Create .gitignore
cat > .gitignore <<EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Secrets
*.enc
config/secrets.yaml
!config/secrets.yaml.example

# OS
.DS_Store
Thumbs.db

# Logs
*.log
EOF

# Create pyproject.toml if it doesn't exist
if [ ! -f "$EXPORT_DIR/pyproject.toml" ]; then
  cat > "$EXPORT_DIR/pyproject.toml" <<EOF
[tool.poetry]
name = "$PROJECT_NAME"
version = "$PROJECT_VERSION"
description = "Data pipeline project"
authors = ["Your Team <team@company.com>"]

[tool.poetry.dependencies]
python = "^3.9"
data-platform-common = { git = "https://github.com/bayleafwalker/datacluster.git", subdirectory = "data-platform/common", tag = "v0.5.0" }
pyspark = "^3.5.0"
delta-spark = "^3.0.0"

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-spark = "^0.6.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
EOF
fi

# Create GitHub Actions workflow
mkdir -p .github/workflows
cat > .github/workflows/test-and-deploy.yaml <<EOF
name: Test and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest tests/ --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          docker build -t ghcr.io/\${{ github.repository }}/$PROJECT_NAME:\${{ github.sha }} .
          docker tag ghcr.io/\${{ github.repository }}/$PROJECT_NAME:\${{ github.sha }} \\
                     ghcr.io/\${{ github.repository }}/$PROJECT_NAME:latest
      
      - name: Push to registry
        run: |
          echo "\${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u \${{ github.actor }} --password-stdin
          docker push ghcr.io/\${{ github.repository }}/$PROJECT_NAME:\${{ github.sha }}
          docker push ghcr.io/\${{ github.repository }}/$PROJECT_NAME:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Kubernetes
        run: |
          # Configure kubectl
          # kubectl apply -k k8s/overlays/prod/
          echo "Deploy step - configure for your cluster"
EOF

# Move project to root
mv "$EXPORT_DIR"/* .
mv "$EXPORT_DIR"/.* . 2>/dev/null || true
rmdir "$EXPORT_DIR"

# Initial commit
git add .
git commit -m "Initial export from datacluster monorepo

Project: $PROJECT_NAME
Version: $PROJECT_VERSION
Export date: $(date -u +"%Y-%m-%d")
"

# Add remote and push
echo ""
echo "🚀 Pushing to remote repository..."
git remote add origin "$TARGET_REPO"

read -p "Push to $TARGET_REPO? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  git push -u origin main
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "✅ Project exported successfully!"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "🎯 Repository: $TARGET_REPO"
  echo "📁 Local copy: $TEMP_DIR"
  echo ""
  echo "Next steps:"
  echo "  1. Review the exported repository"
  echo "  2. Update PROJECT.yaml with new repository URL"
  echo "  3. Configure CI/CD secrets in GitHub"
  echo "  4. Set up branch protection rules"
  echo "  5. Update team access permissions"
  echo ""
  echo "Keep local copy? (Otherwise will be deleted)"
  read -p "Keep? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    cd /
    rm -rf "$TEMP_DIR"
    echo "🗑️  Cleaned up temporary files"
  fi
else
  echo "❌ Export cancelled"
  echo "📁 Local copy available at: $TEMP_DIR"
fi
