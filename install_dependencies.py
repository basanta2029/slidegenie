#!/usr/bin/env python3
"""
Install optional dependencies for enhanced SlideGenie features
"""

import subprocess
import sys
import importlib

def install_package(package_name):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False

def check_package(package_name):
    """Check if a package is installed"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def main():
    """Install optional dependencies"""
    print("🚀 Installing SlideGenie enhanced features...")
    
    # Core dependencies (should already be installed)
    core_deps = [
        "streamlit",
        "python-pptx", 
        "pillow",
        "openai",
        "scikit-learn",
        "numpy"
    ]
    
    # Optional enhanced dependencies
    enhanced_deps = [
        "sentence-transformers",
        "transformers",
        "torch"
    ]
    
    print("\n📋 Checking core dependencies...")
    for dep in core_deps:
        if check_package(dep):
            print(f"✅ {dep} - installed")
        else:
            print(f"❌ {dep} - missing")
            if install_package(dep):
                print(f"✅ {dep} - installed successfully")
            else:
                print(f"❌ {dep} - installation failed")
    
    print("\n🎯 Installing enhanced features...")
    for dep in enhanced_deps:
        print(f"Installing {dep}...")
        if install_package(dep):
            print(f"✅ {dep} - installed successfully")
        else:
            print(f"⚠️  {dep} - installation failed (will use fallback)")
    
    print("\n🎉 Installation complete!")
    print("SlideGenie will automatically use enhanced features when available.")

if __name__ == "__main__":
    main()