# ISA Change Workflow

## Impact Analysis: When ISA Changes

When the Instruction Set Architecture (ISA) changes, multiple components need to be updated. This document outlines the complete workflow.

## Components Affected by ISA Changes

### 1. Hardware (RTL) ✅ Covered by Current Flow
**Location:** `tpu/tensorcore/`

**What Changes:**
- `decoder.sv` - Instruction decode logic
- ISA documentation in comments/headers

**Current Build Flow:**
```bash
make -C tpu bitstream TARGET=ultra96-v2
```
✅ **Auto-handled** - RTL changes are automatically picked up by synthesis

**Verification:**
- Rebuild bitstream (captures new decoder)
- Run board tests

---

### 2. Compiler/Assembler ⚠️ NOT Fully Covered
**Location:** `compiler/`

**What Changes:**
- `compiler/assembler.py` - Instruction encoding
- `compiler/kernels/` - Kernel implementations using new instructions
- `compiler/tpu_txt.py` - TPU assembly syntax

**Current Flow Gaps:**
- ❌ No automated check that compiler matches RTL ISA
- ❌ No ISA version tracking
- ❌ Compiler tests not integrated into board-test flow

**What Should Change:**
1. **Add ISA version constant** in both RTL and compiler
2. **Version check** during bitstream programming
3. **Compiler unit tests** for instruction encoding

---

### 3. Test Programs ⚠️ Partially Covered
**Location:** `tests/ultra96-v2/programs/`

**What Changes:**
- Program definitions if they use new instructions
- Memory layouts if ISA changes data formats

**Current Flow:**
```bash
python tests/ultra96-v2/programs/comprehensive.py  # Recompile
make board-comprehensive                            # Test
```

✅ **Partially handled** - Programs are recompiled, but no validation that they match ISA

**What Should Change:**
1. **ISA-aware program generator** - annotate which ISA version each program targets
2. **Compiler warning** if using deprecated instructions

---

### 4. Documentation ❌ NOT Covered
**Location:** `docs/`

**What Changes:**
- ISA specification (currently no formal spec!)
- Instruction encoding tables
- Example programs

**Current Flow:**
- ❌ No automation - manual updates required

**What Should Change:**
1. **Create formal ISA spec** (`docs/isa.md`)
2. **Auto-generate** instruction tables from decoder RTL
3. **Versioned ISA docs** in git

---

## Recommended Changes for ISA Evolution

### Phase 1: Version Tracking (High Priority)

**1. Add ISA Version to RTL**
```systemverilog
// tpu/tensorcore/decoder.sv
localparam ISA_VERSION = 8'h01;  // v0.1
```

**2. Add ISA Version to Compiler**
```python
# compiler/assembler.py
ISA_VERSION = "0.1"
ISA_MAGIC = 0x54505501  # "TPU" + version 0x01
```

**3. Bitstream Metadata**
- Embed ISA version in bitstream metadata
- Driver checks version on init:
```python
def __init__(self, bitstream):
    self.isa_version = read_isa_version_from_bitstream()
    if self.isa_version != COMPILER_ISA_VERSION:
        raise IncompatibleISAError(...)
```

### Phase 2: Formal ISA Specification (Medium Priority)

**1. Create `docs/isa.md`**
```markdown
# Mini-TPU ISA v0.1

## Instruction Format
[63:58] opcode
[57:52] dest
[51:46] src1
[45:40] src2
...

## Instruction Set
| Opcode | Mnemonic | Operation | Format |
|--------|----------|-----------|--------|
| 0x00   | NOP      | No operation | - |
| 0x01   | VADD     | Vec add   | R-type |
...
```

**2. Auto-Generate from RTL**
```bash
# Extract opcodes from decoder.sv
scripts/extract_isa_from_rtl.py tpu/tensorcore/decoder.sv > docs/isa_generated.md
```

### Phase 3: Compiler-RTL Consistency Checks (High Priority)

**1. Add Compiler Tests**
```python
# tests/test_compiler/test_isa_consistency.py
def test_opcode_matches_rtl():
    """Verify compiler opcodes match RTL decoder."""
    rtl_opcodes = extract_opcodes_from_rtl("tpu/tensorcore/decoder.sv")
    compiler_opcodes = assembler.OPCODE_MAP
    assert rtl_opcodes == compiler_opcodes
```

**2. Add to CI/Board Test Flow**
```bash
# Before board tests
make test-isa-consistency  # Fails if compiler/RTL mismatch
```

### Phase 4: Backward Compatibility Strategy (Low Priority)

For production systems supporting multiple ISA versions:

**1. Multi-Version Compiler**
```python
class Assembler:
    def __init__(self, target_isa="latest"):
        self.isa = load_isa_version(target_isa)
```

**2. Bitstream ISA Reporting**
```python
tpu = TpuDriver(bitstream)
print(f"TPU ISA: {tpu.isa_version}")
```

**3. Feature Detection**
```python
if tpu.supports_instruction("VDIV"):
    prog.emit("VDIV", ...)
else:
    prog.emit_division_workaround(...)
```

---

## Updated Build & Test Flow for ISA Changes

### Current Flow (Partial Coverage)
```bash
# 1. Modify RTL decoder
vim tpu/tensorcore/decoder.sv

# 2. Modify compiler (manual sync)
vim compiler/assembler.py

# 3. Rebuild bitstream
make -C tpu bitstream TARGET=ultra96-v2

# 4. Test (no ISA validation!)
make -C tests board-comprehensive BIT=... HWH=...
```

### Recommended Flow (Full Coverage)
```bash
# 1. Update ISA version constant
vim tpu/tensorcore/decoder.sv        # ISA_VERSION++
vim compiler/assembler.py             # ISA_VERSION++

# 2. Modify decoder RTL
vim tpu/tensorcore/decoder.sv

# 3. Modify compiler to match
vim compiler/assembler.py

# 4. Verify consistency (NEW)
make test-isa-consistency  # Fails if mismatch

# 5. Update formal spec (NEW)
scripts/generate_isa_docs.py

# 6. Rebuild bitstream
make -C tpu bitstream TARGET=ultra96-v2

# 7. Run compiler unit tests (NEW)
pytest tests/test_compiler/

# 8. Recompile test programs
python tests/ultra96-v2/programs/*.py

# 9. Board test with version check
make -C tests board-comprehensive BIT=... HWH=...
# (Driver auto-checks ISA version match)
```

---

## Implementation Checklist

**Immediate (Can Implement Now):**
- [ ] Add ISA version constants to RTL and compiler
- [ ] Create `docs/isa.md` with current instruction set
- [ ] Add compiler unit tests (`tests/test_compiler/`)
- [ ] Document ISA change workflow (this file)

**Short-term (Next Sprint):**
- [ ] Add ISA version check to TpuDriver init
- [ ] Create ISA consistency test
- [ ] Add "ISA-Version" field to bitstream metadata/HWH
- [ ] Integrate compiler tests into board-test flow

**Long-term (Future):**
- [ ] Auto-generate ISA docs from RTL
- [ ] Multi-version compiler support
- [ ] Feature detection API
- [ ] ISA versioning in CI

---

## Example: Adding a New Instruction

**Scenario:** Add `VMAX` (vector maximum) instruction

**Step-by-Step:**

1. **Update ISA Version**
   ```systemverilog
   // decoder.sv
   localparam ISA_VERSION = 8'h02;  // v0.1 -> v0.2
   ```

2. **Add to RTL Decoder**
   ```systemverilog
   // decoder.sv
   localparam OPCODE_VMAX = 6'b010101;

   case (opcode)
       OPCODE_VMAX: begin
           unit_sel = UNIT_VPU;
           vpu_op = VPU_OP_MAX;
       end
   ```

3. **Add to VPU**
   ```systemverilog
   // vpu_op.sv
   localparam VPU_OP_MAX = 3'd5;

   case (op)
       VPU_OP_MAX: result = (a > b) ? a : b;
   ```

4. **Update Compiler**
   ```python
   # assembler.py
   ISA_VERSION = "0.2"

   OPCODE_MAP = {
       "VMAX": 0b010101,
       ...
   }
   ```

5. **Add Kernel**
   ```python
   # compiler/kernels/vpu.py
   def vmax(prog, src_a, src_b, dest):
       prog.emit("VMAX", dest=dest, src1=src_a, src2=src_b)
   ```

6. **Add Test**
   ```python
   # tests/test_compiler/test_vmax.py
   def test_vmax_encoding():
       prog = Program()
       prog.emit("VMAX", dest=0, src1=1, src2=2)
       assert prog.instructions[0] & 0xFC == (0b010101 << 58)
   ```

7. **Rebuild & Test**
   ```bash
   make test-isa-consistency  # Verify sync
   make -C tpu bitstream TARGET=ultra96-v2
   pytest tests/test_compiler/
   make -C tests board-comprehensive BIT=... HWH=...
   ```

---

## Conclusion

**Current State:**
- ✅ Hardware changes flow through rebuild automatically
- ⚠️ Compiler changes have no validation against RTL
- ❌ No ISA versioning or compatibility checks

**Recommended Additions:**
1. ISA version tracking (RTL + compiler)
2. Formal ISA specification
3. Compiler-RTL consistency tests
4. Runtime version checking

**Impact on Build Flow:**
- Add pre-build ISA consistency check
- Add compiler unit tests to validation
- Add ISA version to bitstream metadata

With these changes, ISA evolution becomes **safe and traceable**.
