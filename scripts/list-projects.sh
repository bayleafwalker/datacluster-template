#!/bin/bash
# List all projects in data-platform/projects/
# Usage: ./list-projects.sh [--format=table|json|yaml]

FORMAT=${1:-table}
FORMAT=${FORMAT#--format=}

PROJECTS_DIR="$(cd "$(dirname "$0")/../data-platform/projects" && pwd)"

if [ ! -d "$PROJECTS_DIR" ]; then
  echo "❌ Projects directory not found: $PROJECTS_DIR"
  exit 1
fi

# Function to parse YAML field
parse_yaml() {
  local file=$1
  local field=$2
  grep "^${field}:" "$file" 2>/dev/null | head -1 | cut -d'"' -f2 | xargs || echo "N/A"
}

# Collect project information
PROJECTS=()
cd "$PROJECTS_DIR"
for project_dir in */; do
  project_name=$(basename "$project_dir")
  
  # Skip template and hidden directories
  if [[ "$project_name" == "_"* ]] || [[ "$project_name" == "."* ]]; then
    continue
  fi
  
  project_file="$project_dir/PROJECT.yaml"
  
  if [ -f "$project_file" ]; then
    name=$(parse_yaml "$project_file" "name")
    version=$(parse_yaml "$project_file" "version")
    status=$(parse_yaml "$project_file" "status")
    team=$(parse_yaml "$project_file" "team" | head -1)
    description=$(parse_yaml "$project_file" "description")
    
    PROJECTS+=("$project_name|$name|$version|$status|$team|$description")
  else
    PROJECTS+=("$project_name|N/A|N/A|N/A|N/A|Missing PROJECT.yaml")
  fi
done

# Sort projects
IFS=$'\n' PROJECTS=($(sort <<<"${PROJECTS[*]}"))
unset IFS

# Output based on format
case "$FORMAT" in
  table)
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%-25s %-12s %-12s %-10s %s\n" "PROJECT" "VERSION" "STATUS" "TEAM" "DESCRIPTION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for project in "${PROJECTS[@]}"; do
      IFS='|' read -r dir name version status team description <<< "$project"
      printf "%-25s %-12s %-12s %-10s %s\n" "$name" "$version" "$status" "$team" "${description:0:40}"
    done
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Total projects: ${#PROJECTS[@]}"
    ;;
    
  json)
    echo "{"
    echo "  \"projects\": ["
    
    first=true
    for project in "${PROJECTS[@]}"; do
      IFS='|' read -r dir name version status team description <<< "$project"
      
      if [ "$first" = true ]; then
        first=false
      else
        echo ","
      fi
      
      echo -n "    {"
      echo -n "\"directory\":\"$dir\","
      echo -n "\"name\":\"$name\","
      echo -n "\"version\":\"$version\","
      echo -n "\"status\":\"$status\","
      echo -n "\"team\":\"$team\","
      echo -n "\"description\":\"$description\""
      echo -n "}"
    done
    
    echo ""
    echo "  ],"
    echo "  \"total\": ${#PROJECTS[@]}"
    echo "}"
    ;;
    
  yaml)
    echo "projects:"
    for project in "${PROJECTS[@]}"; do
      IFS='|' read -r dir name version status team description <<< "$project"
      echo "  - directory: \"$dir\""
      echo "    name: \"$name\""
      echo "    version: \"$version\""
      echo "    status: \"$status\""
      echo "    team: \"$team\""
      echo "    description: \"$description\""
    done
    echo "total: ${#PROJECTS[@]}"
    ;;
    
  *)
    echo "❌ Unknown format: $FORMAT"
    echo "Usage: $0 [--format=table|json|yaml]"
    exit 1
    ;;
esac
