# Compiler

TPU instruction encoding and module generation.

## Contents

| File | Description |
|------|-------------|
| `assembler.py` | Instruction encoder (generates hex from assembly) |
| `tpu_txt.py` | High-level IR emission (load, store, matmul, etc.) |
| `module.py` | [PLANNED] TPUModule packaging for AOT compilation |

## Usage

```python
from compiler.tpu_txt import matmul, load, store, get_instruction_log
from compiler.assembler import assemble_file

# Emit instructions
load(0, my_weights)
matmul(0, 16, 32)
store(32, 16, "output")

# Assemble to hex
assemble_file("instructions.txt", "instructions.hex")
```

## Architecture

```
tpu_txt.py (IR)  →  assembler.py (encoder)  →  .hex / TPUModule
```
