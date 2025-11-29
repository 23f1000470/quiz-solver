#!/usr/bin/env python3
import subprocess
import sys
import os

def install_requirements():
    """Install requirements and setup Playwright"""
    print("Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    print("Installing Playwright browsers...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    
    print("Setup completed successfully!")

if __name__ == "__main__":
    install_requirements()