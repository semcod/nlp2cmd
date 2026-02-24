#!/usr/bin/env python3
"""
Final Integration Script for Polish Language Support
Applies all patches and enables Polish language support in NLP2CMD
"""

import shutil
import sys
from pathlib import Path

def apply_core_patch():
    """Apply core patch"""
    print("🔧 Applying core patch...")
    
    core_backup = Path("src/nlp2cmd/core_backup.py")
    core_patched = Path("src/nlp2cmd/core_patched.py")
    core_current = Path("src/nlp2cmd/core.py")
    
    if core_patched.exists():
        # Backup current core
        if core_current.exists():
            shutil.copy2(core_current, core_backup)
        
        # Apply patch
        shutil.copy2(core_patched, core_current)
        print("✅ Core patch applied")
        return True
    else:
        print("❌ Core patch not found")
        return False

def apply_adapter_patches():
    """Apply adapter patches"""
    print("🔧 Applying adapter patches...")
    
    adapters = [
        "src/nlp2cmd/adapters/shell.py",
        "src/nlp2cmd/adapters/sql.py", 
        "src/nlp2cmd/adapters/docker.py",
        "src/nlp2cmd/adapters/kubernetes.py"
    ]
    
    success_count = 0
    
    for adapter in adapters:
        adapter_path = Path(adapter)
        patched_path = adapter_path.replace('.py', '_patched.py')
        
        if patched_path.exists():
            # Apply patch
            shutil.copy2(patched_path, adapter_path)
            print(f"✅ {adapter} patch applied")
            success_count += 1
        else:
            print(f"❌ {adapter} patch not found")
    
    return success_count == len(adapters)

def verify_integration():
    """Verify integration"""
    print("🔍 Verifying integration...")
    
    try:
        # Try to import Polish support
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from nlp2cmd.polish_support import get_polish_support
        polish_support = get_polish_support()
        
        print("✅ Polish support module imported successfully")
        
        # Check if patterns are loaded
        if polish_support.patterns:
            print(f"✅ Polish patterns loaded: {len(polish_support.patterns)} categories")
        
        if polish_support.intent_mappings:
            print(f"✅ Intent mappings loaded: {len(polish_support.intent_mappings)} mappings")
        
        if polish_support.table_mappings:
            print(f"✅ Table mappings loaded: {len(polish_support.table_mappings)} mappings")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration verification failed: {e}")
        return False

def main():
    """Main integration function"""
    print("🚀 Applying Polish Language Support Integration")
    print("=" * 60)
    
    # Apply core patch
    core_success = apply_core_patch()
    
    # Apply adapter patches
    adapters_success = apply_adapter_patches()
    
    # Verify integration
    verification_success = verify_integration()
    
    print("\n" + "=" * 60)
    print("🎯 INTEGRATION RESULTS")
    print("=" * 60)
    
    print(f"Core patch: {'✅ Applied' if core_success else '❌ Failed'}")
    print(f"Adapter patches: {'✅ Applied' if adapters_success else '❌ Failed'}")
    print(f"Verification: {'✅ Passed' if verification_success else '❌ Failed'}")
    
    if core_success and adapters_success and verification_success:
        print("\n🎉 Integration successful!")
        print("Polish language support is now enabled in NLP2CMD")
        print("\nNext steps:")
        print("1. Test Polish commands")
        print("2. Run comprehensive test suite")
        print("3. Monitor performance improvements")
    else:
        print("\n⚠️  Integration incomplete")
        print("Please check the errors above and retry")
    
    return core_success and adapters_success and verification_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
