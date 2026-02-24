#!/usr/bin/env python3

"""Debug script for n_samples issue with detailed tracking."""

import sys
sys.path.insert(0, '/home/tom/github/wronai/nlp2cmd/src')

from nlp2cmd.generation.thermodynamic import create_thermodynamic_generator

def debug_detailed():
    """Debug n_samples configuration in detail."""
    print("=== Detailed Debugging of n_samples issue ===")
    
    # Create generator exactly like in the failing test
    generator = create_thermodynamic_generator(n_samples=3, n_steps=100, adaptive_steps=False)
    
    print(f"Generator config.n_samples: {generator.config.n_samples}")
    print(f"Generator adaptive_steps: {generator.adaptive_steps}")
    
    # Test generation and track what happens
    import asyncio
    async def test_generation():
        print("Starting generation...")
        
        # Monkey patch to track what config is used
        original_generate = generator.generate
        
        async def tracked_generate(text, problem=None, context=None):
            print(f"Inside generate, adaptive_steps={generator.adaptive_steps}")
            
            if problem is None:
                problem = generator.problem_detector.detect_problem(text)
                if problem is None:
                    return None
                print(f"Detected problem: {problem}")
                print(f"Problem variables: {problem.variables}")
                print(f"Problem n_tasks: {problem.n_tasks}")
                print(f"Problem n_slots: {problem.n_slots}")
            
            # Check what config will be used
            if generator.adaptive_steps:
                config = generator.config.adapt_to_problem_size(problem)
                print(f"Using ADAPTED config: n_samples={config.n_samples}")
            else:
                config = generator.config
                print(f"Using ORIGINAL config: n_samples={config.n_samples}")
            
            return await original_generate(text, problem, context)
        
        generator.generate = tracked_generate
        
        result = await generator.generate("Zaplanuj 3 zadania w 5 slotach")
        print(f"Final result n_samples: {result.n_samples}")
        return result
    
    result = asyncio.run(test_generation())
    return result

if __name__ == "__main__":
    debug_detailed()
