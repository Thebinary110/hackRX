#!/bin/bash

echo "🔧 Installing PDF processing libraries..."

# Install PyMuPDF (recommended)
echo "📦 Installing PyMuPDF..."
pip install PyMuPDF

# Install PyPDF2 as backup
echo "📦 Installing PyPDF2..."
pip install PyPDF2

# Install pdfplumber as another backup
echo "📦 Installing pdfplumber..."
pip install pdfplumber

# Install other dependencies
echo "📦 Installing other document processing dependencies..."
pip install python-docx
pip install beautifulsoup4
pip install chardet
pip install requests
pip install pillow
pip install pytesseract

echo "✅ Installation complete!"

echo "🧪 Testing PDF libraries..."
python -c "
try:
    import fitz
    print('✅ PyMuPDF (fitz) imported successfully')
    print(f'   Version: {fitz.__version__ if hasattr(fitz, \"__version__\") else \"Unknown\"}')
    
    # Test opening a simple PDF
    doc = fitz.open()  # Create empty document
    doc.close()
    print('✅ PyMuPDF can create/open documents')
except Exception as e:
    print(f'❌ PyMuPDF error: {e}')

try:
    import PyPDF2
    print('✅ PyPDF2 imported successfully')
    print(f'   Version: {PyPDF2.__version__ if hasattr(PyPDF2, \"__version__\") else \"Unknown\"}')
except Exception as e:
    print(f'❌ PyPDF2 error: {e}')

try:
    import pdfplumber
    print('✅ pdfplumber imported successfully')
    print(f'   Version: {pdfplumber.__version__ if hasattr(pdfplumber, \"__version__\") else \"Unknown\"}')
except Exception as e:
    print(f'❌ pdfplumber error: {e}')
"

echo "🏁 Done! Check the output above for any remaining issues."