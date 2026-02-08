#!/usr/bin/env python3
import os
import re

def clean_serbian_chars(text):
    """Replace Serbian characters with ASCII equivalents"""
    replacements = {
        'c': 'c', 'C': 'C',
        'c': 'c', 'C': 'C', 
        's': 's', 'S': 'S',
        'd': 'd', 'D': 'D',
        'z': 'z', 'Z': 'Z'
    }
    
    for serbian, ascii_char in replacements.items():
        text = text.replace(serbian, ascii_char)
    
    return text

def clean_file(filepath):
    """Clean Serbian chars from a Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content = clean_serbian_chars(content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[CLEANED] {filepath}")
            return True
        else:
            print(f"[OK] {filepath}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {filepath}: {e}")
        return False

def main():
    print("Cleaning Serbian characters from Python files...")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    cleaned_count = 0
    for filepath in python_files:
        if clean_file(filepath):
            cleaned_count += 1
    
    print(f"\nFinished! Cleaned {cleaned_count} files out of {len(python_files)} Python files.")

if __name__ == "__main__":
    main()