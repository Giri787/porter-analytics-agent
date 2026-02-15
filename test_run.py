"""
Quick test script to verify the agent works with your sample data.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from main import main

if __name__ == '__main__':
    print("=" * 60)
    print("Porter Analytics Agent - Quick Test")
    print("=" * 60)
    print()
    print("This will test the agent with your sample Excel file.")
    print("No emails will be sent.")
    print()
    
    # Path to your sample file
    sample_file = r"C:\Users\anubh\Downloads\Porter analysis.xlsx"
    
    if not os.path.exists(sample_file):
        print(f"❌ Sample file not found: {sample_file}")
        print("Please update the path in test_run.py")
        sys.exit(1)
    
    print(f"📄 Using sample file: {sample_file}")
    print()
    print("Running analysis...")
    print()
    
    success = main(
        test_mode=True,
        input_file=sample_file,
        fetch_email=False
    )
    
    if success:
        print()
        print("=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        print()
        print("📊 Check the data/reports/ folder for the generated report")
        print("🌐 Open the HTML file in your browser to view the report")
        print()
    else:
        print()
        print("=" * 60)
        print("❌ Test failed - check porter_analytics.log for details")
        print("=" * 60)
        print()
    
    sys.exit(0 if success else 1)
