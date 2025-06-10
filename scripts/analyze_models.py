#!/bin/bash
# Quick fix script to convert models.py to models/__init__.py

echo "🔧 Converting models.py to models/ directory structure..."

# Check if models.py exists
if [ ! -f "models.py" ]; then
    echo "❌ Error: models.py not found!"
    exit 1
fi

# Check if models/ directory already exists
if [ -d "models/" ]; then
    echo "⚠️  models/ directory already exists!"
    echo "   Please check what's inside and handle manually"
    ls -la models/
    exit 1
fi

# Create models directory
mkdir models/
echo "✅ Created models/ directory"

# Move models.py content to models/__init__.py
cp models.py models/__init__.py
echo "✅ Copied models.py to models/__init__.py"

# Backup original models.py
mv models.py models_backup.py
echo "✅ Backed up original models.py to models_backup.py"

echo ""
echo "🎉 Conversion complete!"
echo "   📂 Your models are now in: models/__init__.py"
echo "   💾 Original backed up as: models_backup.py"
echo "   🚀 You can now run: python app.py"
echo ""
echo "If you still get errors, run: python analyze_models.py"