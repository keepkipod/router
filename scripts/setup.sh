#!/bin/bash
set -euo pipefail

echo "🚀 Setting up Cell Router Project..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ Git is required but not installed."; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
make install-dependencies

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p k8s/{argocd/applications,nginx/{nginx-1,nginx-2,nginx-3},router,monitoring}
mkdir -p router/{src,tests}

# Copy nginx configurations
echo "📋 Setting up NGINX configurations..."
for i in 2 3; do
  if [ -d "k8s/nginx/nginx-1" ]; then
    cp -r k8s/nginx/nginx-1/* k8s/nginx/nginx-$i/
    find k8s/nginx/nginx-$i/ -type f -exec sed -i "s/nginx-1/nginx-$i/g; s/cell: \"1\"/cell: \"$i\"/g; s/Cell 1/Cell $i/g; s/\"1\"/\"$i\"/g" {} \;
  fi
done

echo "✅ Setup complete! Next steps:"
echo "1. Update Git repository URLs in k8s/argocd/applications/*.yaml"
echo "2. Run: task deploy-all-argocd"
echo "3. Build router: task build-app"
