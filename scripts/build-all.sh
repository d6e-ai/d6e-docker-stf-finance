#!/bin/bash
# Build all D6E Finance STF Docker images
#
# Usage: ./scripts/build-all.sh [--push]
#
# Options:
#   --push    Push images to registry after building

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Image tag
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-}"

# STF directories
STFS=(
    "stf-financial-statements"
    "stf-journal-entry"
    "stf-variance-analysis"
    "stf-reconciliation"
    "stf-close-management"
)

echo "========================================"
echo "D6E Finance STF Builder"
echo "========================================"
echo "Tag: $TAG"
echo "Registry: ${REGISTRY:-local}"
echo ""

# Copy shared utilities to each STF directory
echo "Copying shared utilities..."
for stf in "${STFS[@]}"; do
    STF_DIR="$PROJECT_ROOT/$stf"
    if [ -d "$STF_DIR" ]; then
        mkdir -p "$STF_DIR/shared"
        cp "$PROJECT_ROOT/shared/utils.py" "$STF_DIR/shared/"
        echo "  Copied to $stf/shared/"
    fi
done

# Build each STF
echo ""
echo "Building Docker images..."
for stf in "${STFS[@]}"; do
    STF_DIR="$PROJECT_ROOT/$stf"
    
    if [ -d "$STF_DIR" ] && [ -f "$STF_DIR/Dockerfile" ]; then
        echo ""
        echo "----------------------------------------"
        echo "Building: $stf"
        echo "----------------------------------------"
        
        if [ -n "$REGISTRY" ]; then
            IMAGE_NAME="$REGISTRY/$stf:$TAG"
        else
            IMAGE_NAME="$stf:$TAG"
        fi
        
        docker build -t "$IMAGE_NAME" "$STF_DIR"
        
        echo "✓ Built: $IMAGE_NAME"
        
        # Push if requested
        if [ "$1" == "--push" ] && [ -n "$REGISTRY" ]; then
            echo "Pushing: $IMAGE_NAME"
            docker push "$IMAGE_NAME"
            echo "✓ Pushed: $IMAGE_NAME"
        fi
    else
        echo "⚠ Skipping $stf (no Dockerfile found)"
    fi
done

# Clean up copied shared files
echo ""
echo "Cleaning up..."
for stf in "${STFS[@]}"; do
    rm -rf "$PROJECT_ROOT/$stf/shared"
done

echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo ""
echo "Images built:"
for stf in "${STFS[@]}"; do
    if [ -n "$REGISTRY" ]; then
        echo "  - $REGISTRY/$stf:$TAG"
    else
        echo "  - $stf:$TAG"
    fi
done

echo ""
echo "Test with:"
echo '  echo '"'"'{"workspace_id":"test","stf_id":"test","caller":null,"api_url":"http://localhost:8080","api_token":"test","input":{"operation":"generate_trial_balance","period":"2025-01"},"sources":{}}'"'"' | docker run --rm -i stf-financial-statements:latest'
