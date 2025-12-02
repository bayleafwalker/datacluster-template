#!/bin/bash
# Import external project into data-platform/projects/
# Usage: ./import-project.sh <git-repo-url> [target-name]

set -e

REPO_URL=$1
TARGET_NAME=${2:-$(basename $REPO_URL .git)}

if [ -z "$REPO_URL" ]; then
  echo "❌ Usage: $0 <git-repo-url> [target-name]"
  echo ""
  echo "Example:"
  echo "  $0 https://github.com/company/fraud-detection fraud-detection"
  exit 1
fi

PROJECTS_DIR="$(cd "$(dirname "$0")/../data-platform/projects" && pwd)"
TARGET_DIR="$PROJECTS_DIR/$TARGET_NAME"

echo "📦 Importing project from: $REPO_URL"
echo "📁 Target directory: $TARGET_DIR"
echo ""

# Check if target already exists
if [ -d "$TARGET_DIR" ]; then
  echo "⚠️  Directory $TARGET_DIR already exists!"
  read -p "Overwrite? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted"
    exit 1
  fi
  rm -rf "$TARGET_DIR"
fi

# Clone repository
echo "⬇️  Cloning repository..."
git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
rm -rf "$TARGET_DIR/.git"  # Remove git history

# Validate project structure
echo "✅ Validating project structure..."

REQUIRED_FILES=(
  "PROJECT.yaml"
  "README.md"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$TARGET_DIR/$file" ]; then
    MISSING_FILES+=("$file")
  fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
  echo "❌ Invalid project structure. Missing required files:"
  for file in "${MISSING_FILES[@]}"; do
    echo "   - $file"
  done
  echo ""
  echo "Required structure:"
  echo "  project-name/"
  echo "  ├── PROJECT.yaml     # Project metadata"
  echo "  ├── README.md        # Documentation"
  echo "  ├── config/          # Configuration files"
  echo "  ├── src/             # Source code"
  echo "  ├── tests/           # Tests"
  echo "  ├── k8s/             # Kubernetes manifests"
  echo "  └── docs/            # Documentation"
  exit 1
fi

# Parse PROJECT.yaml
echo "📋 Reading project metadata..."
PROJECT_NAME=$(grep "^name:" "$TARGET_DIR/PROJECT.yaml" | cut -d'"' -f2 | xargs)
PROJECT_VERSION=$(grep "^version:" "$TARGET_DIR/PROJECT.yaml" | cut -d'"' -f2 | xargs)
PROJECT_OWNER=$(grep "team:" "$TARGET_DIR/PROJECT.yaml" | head -1 | cut -d'"' -f2 | xargs)

if [ -z "$PROJECT_NAME" ]; then
  echo "⚠️  Warning: Could not parse project name from PROJECT.yaml"
  PROJECT_NAME=$TARGET_NAME
fi

echo ""
echo "📦 Project: $PROJECT_NAME"
echo "🔖 Version: $PROJECT_VERSION"
echo "👥 Owner: $PROJECT_OWNER"
echo ""

# Check dependencies
echo "🔍 Checking dependencies..."
if [ -f "$TARGET_DIR/requirements.txt" ]; then
  echo "   Found requirements.txt"
  if grep -q "data.platform.common" "$TARGET_DIR/requirements.txt" 2>/dev/null || \
     grep -q "data_platform_common" "$TARGET_DIR/requirements.txt" 2>/dev/null; then
    echo "   ✅ Project uses data-platform-common"
  else
    echo "   ⚠️  Warning: Project may not use common libraries"
  fi
fi

if [ -f "$TARGET_DIR/pyproject.toml" ]; then
  echo "   Found pyproject.toml"
fi

# Update repository reference in PROJECT.yaml
echo "📝 Updating repository reference..."
sed -i.bak "s|url:.*|url: \"$REPO_URL\"|g" "$TARGET_DIR/PROJECT.yaml" 2>/dev/null || true
rm -f "$TARGET_DIR/PROJECT.yaml.bak"

# Create import metadata
cat > "$TARGET_DIR/.import-metadata.yaml" <<EOF
imported_from: "$REPO_URL"
imported_at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
imported_by: "$(git config user.email 2>/dev/null || echo 'unknown')"
original_name: "$TARGET_NAME"
EOF

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Project imported successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Location: $TARGET_DIR"
echo ""
echo "Next steps:"
echo "  1. Review PROJECT.yaml configuration"
echo "  2. Update config/pipeline.yaml for your environment"
echo "  3. Install dependencies:"
echo "     cd $TARGET_DIR && pip install -r requirements.txt"
echo "  4. Run tests:"
echo "     cd $TARGET_DIR && pytest tests/"
echo "  5. Build Docker image:"
echo "     cd data-platform && docker build -t datacluster-data:latest ."
echo "  6. Deploy to cluster:"
echo "     kubectl apply -k $TARGET_DIR/k8s/overlays/dev/"
echo ""
