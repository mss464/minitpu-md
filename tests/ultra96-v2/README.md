# Ultra96-v2 FPGA Tests

## Comprehensive Test

Tests VPU operations, 4x4 matmul, and 8x8 tiled matmul using the kernel API.

### Workflow

**Quick Start (Automated):**
```bash
# Build bitstream and run tests
agent-skills/ultra96-v2/validate/scripts/build_and_test.sh --board-ip <ip>

# Test only (skip build)
agent-skills/ultra96-v2/validate/scripts/build_and_test.sh --skip-build --board-ip <ip>
```

**Manual Workflow:**

**1. Compile program locally:**
```bash
python tests/ultra96-v2/programs/comprehensive.py
```

Generates:
- `comprehensive.npy` - compiled binary (90 instructions)
- `comprehensive.hex` - human-readable hex
- `comprehensive_meta.json` - memory map

**2. Deploy and run on board:**
```bash
make -C tests board-comprehensive \
  BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
  HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh \
  BOARD_IP=<your-board-ip>
```

Or manually:
```bash
make -C tests board-test \
  BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
  HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh \
  PROGRAM=tests/ultra96-v2/test_comprehensive.py \
  EXTRA_FILES="tests/ultra96-v2/comprehensive.npy tests/ultra96-v2/comprehensive_meta.json" \
  BOARD_IP=<your-board-ip>
```

### Architecture

**Compilation (local):**
- `programs/comprehensive.py` - defines test program using kernel API
- Uses `compiler.program.Program` to compose kernels with memory allocation
- Produces binary + metadata

**Runtime (on board):**
- `test_comprehensive.py` - test harness
- Only depends on `compiler.hal.pynq_host.TpuDriver` (copied by Makefile)
- Loads pre-compiled binary and metadata
- Runs tests and verifies results

**What gets copied to board:**
- Runtime: `compiler/hal/pynq_host.py`
- Test: `test_comprehensive.py`
- Data: `comprehensive.npy`, `comprehensive_meta.json`
- Bitstream: `minitpu.bit`, `minitpu.hwh`

**What stays local:**
- Compiler infrastructure: `compiler/kernel.py`, `compiler/program.py`, `compiler/kernels/`
- Program definitions: `programs/comprehensive.py`

### Adding New Tests

1. Create program definition in `programs/your_test.py`:
```python
from compiler.program import Program
from compiler.kernels import matmul_4x4

prog = Program()
W = prog.alloc("W", 16)
X = prog.alloc("X", 16)
Z = prog.alloc("Z", 16)
prog.call(matmul_4x4, W=W, X=X, Z=Z)
prog.save("your_test.npy")
```

2. Create test harness `test_your_test.py`:
```python
from compiler.hal.pynq_host import TpuDriver
import numpy as np

instructions = np.load("your_test.npy")
tpu = TpuDriver(bitstream)
tpu.write_instructions(instructions)
tpu.compute()
# verify results...
```

3. Run:
```bash
python programs/your_test.py  # compile
make board-test BIT=... PROGRAM=test_your_test.py EXTRA_FILES="your_test.npy"
```
