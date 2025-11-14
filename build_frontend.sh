#!/bin/bash
# Build frontend assets and copy to Django static directory
set -e

echo "Building frontend assets..."
cd frontend
npm install
npm run build
cd ..

echo "Copying assets to Django static directory..."
rm -rf django_email_learning/static/assets
rm -f django_email_learning/static/manifest.json
mkdir -p django_email_learning/static

# Copy only the necessary files
cp -r dist/assets django_email_learning/static/
cp dist/manifest.json django_email_learning/static/

echo "✓ Frontend assets built and copied successfully"
echo "  Assets: django_email_learning/static/assets/"
echo "  Manifest: django_email_learning/static/manifest.json"
