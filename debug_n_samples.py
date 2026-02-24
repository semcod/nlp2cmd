#!/usr/bin/env python3

"""Debug script for n_samples issue."""

import sys
sys.path.insert(0, '/home/tom/github/wronai/nlp2cmd/src')

from nlp2cmd.generation.thermodynamic import create_thermodynamic_generator

def debug_n_samples():
    """Debug n_samples configuration."""
    print("=== Debugging n_samples issue ===")
    
    # Create generator with n_samples=3 (like in test)
    generator = create_thermodynamic_generator(n_samples=3, n_steps=100, adaptive_steps=False)
    
    print(f"Generator config.n_samples: {generator.config.n_samples}")
    print(f"Expected: 3")
    
    # Test generation
    import asyncio
    async def test_generation():
        result = await generator.generate("Zaplanuj 3 zadania w 5 slotach")
        print(f"Result n_samples: {result.n_samples}")
        print(f"Expected: 3")
        return result
    
    result = asyncio.run(test_generation())
    print(f"Final result n_samples: {result.n_samples}")
    
    return result

if __name__ == "__main__":
    debug_n_samples()
