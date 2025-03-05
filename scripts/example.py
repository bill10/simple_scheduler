#!/usr/bin/env python3
import sys
import time
from datetime import datetime

def main():
    # First argument is the start time
    start_time = sys.argv[1]
    print(f"Script started at {start_time}")
    
    # Any additional arguments
    if len(sys.argv) > 2:
        print("Additional arguments:", sys.argv[2:])
    
    # Simulate some work
    print("Working...")
    time.sleep(2)
    print("Work completed!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
