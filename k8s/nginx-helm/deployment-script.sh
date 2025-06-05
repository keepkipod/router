#!/bin/bash
# Script to deploy NGINX cells manually (for testing)

echo "Deploying NGINX Cells with Helm..."

# Deploy Cell 1
echo "Deploying NGINX Cell 1..."
helm upgrade --install nginx-1 ./k8s/nginx-helm \
  -f ./k8s/nginx-helm/values-cell-1.yaml \
  -n nginx \
  --create-namespace

# Deploy Cell 2
echo "Deploying NGINX Cell 2..."
helm upgrade --install nginx-2 ./k8s/nginx-helm \
  -f ./k8s/nginx-helm/values-cell-2.yaml \
  -n nginx \
  --create-namespace

# Deploy Cell 3
echo "Deploying NGINX Cell 3..."
helm upgrade --install nginx-3 ./k8s/nginx-helm \
  -f ./k8s/nginx-helm/values-cell-3.yaml \
  -n nginx \
  --create-namespace

echo "All NGINX cells deployed!"

# Check status
echo ""
echo "Checking deployment status..."
helm list -n nginx
kubectl get pods -n nginx
