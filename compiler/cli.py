#!/usr/bin/env python3
import sys
import os
import argparse
import importlib.util
from typing import List

# Ensure project root is in path
sys.path.append(os.getcwd())

import compiler.tpu_txt as tpu_txt

def load_module_from_path(path: str):
    """Dynamically load a Python module from a file path."""
    module_name = os.path.basename(path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description="Mini-TPU Compiler Frontend CLI")
    parser.add_argument("source", help="Path to Python model file (must verify build() function)")
    parser.add_argument("-o", "--output", required=True, help="Output path for instruction trace")
    args = parser.parse_args()

    print(f"Compiling {args.source}...")
    
    # Reset instruction log before building
    # tpu_txt.instruction_log = [] # Accessing internal list directly or need a clear function?
    # tpu_txt doesn't have clear(). Let's assume it starts empty or we can re-assign.
    tpu_txt.instruction_log = [] 

    # Load user model
    try:
        model_module = load_module_from_path(args.source)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    # Check for build entry point
    if not hasattr(model_module, "build"):
        print(f"Error: Module {args.source} does not define a 'build()' function.")
        sys.exit(1)

    # Execute build
    print("Building model...")
    try:
        model_module.build()
    except Exception as e:
        print(f"Error during build execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Retrieve instructions
    instructions = tpu_txt.get_instruction_log()
    print(f"Generated {len(instructions)} instructions.")

    # Write output
    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    
    with open(args.output, "w") as f:
        for instr in instructions:
            f.write(instr + "\n")
    
    print(f"Trace saved to {args.output}")

if __name__ == "__main__":
    main()
