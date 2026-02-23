#!/usr/bin/env python3
"""
Test user directory command generation.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nlp2cmd.generation.template_generator import TemplateGenerator

def test_user_directory():
    """Test user directory command generation."""
    
    test_cases = [
        ("pokaz pliki usera", "find ~ -type f"),
        ("show user files", "find ~ -type f"),
        ("pokaż pliki użytkownika", "find ~ -type f"),
        ("list user files", "find ~ -type f"),
        ("znajdź pliki w folderze użytkownika", "find ~ -type f"),
    ]
    
    generator = TemplateGenerator()
    
    print("🔍 Testing User Directory Command Generation")
    print("=" * 60)
    
    results = []
    for query, expected_command in test_cases:
        try:
            # Simulate enhanced context entities
            entities = {
                'user': 'current',
                'text': query,
                'language': 'pl' if 'plik' in query or 'pokaż' in query or 'znajdź' in query else 'en'
            }
            
            result = generator.generate('shell', 'find', entities)
            
            success = result.command == expected_command
            
            results.append({
                'query': query,
                'expected': expected_command,
                'actual': result.command,
                'success': success,
                'entities': entities
            })
            
            status = "✅" if success else "❌"
            print(f"{status} '{query}'")
            print(f"   Expected: {expected_command}")
            print(f"   Got: {result.command}")
            print(f"   Entities: {entities}")
            print()
            
        except Exception as e:
            print(f"❌ '{query}' - Error: {e}")
            print()
    
    # Summary
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    success_rate = (successful_tests / total_tests) * 100
    
    print("=" * 60)
    print(f"📊 USER DIRECTORY SUMMARY")
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    
    # Failed tests
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print("❌ Failed Tests:")
        for test in failed_tests:
            print(f"   '{test['query']}'")
            print(f"   Expected: {test['expected']}")
            print(f"   Got: {test['actual']}")
            print()
    
    return success_rate

if __name__ == "__main__":
    success_rate = test_user_directory()
    sys.exit(0 if success_rate >= 80 else 1)
