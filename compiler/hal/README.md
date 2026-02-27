# Hardware Abstraction Layer (HAL)

Per-target driver implementations.

## Contents

| File | Description |
|------|-------------|
| `pynq.py` | PYNQ overlay driver (current FPGA implementation) |
| `simulator.py` | [PLANNED] Software simulation backend |
| `xrt.py` | [PLANNED] XRT/OpenCL driver for Alveo/Versal |
| `asic_gpio.py` | [PLANNED] GPIO protocol driver for taped-out ASIC |

## Interface

All drivers implement the `TPUDevice` interface:

```python
class TPUDevice(ABC):
    def allocate(self, size: int, addr: int) -> DeviceBuffer: ...
    def transfer_h2d(self, data: np.ndarray, buf: DeviceBuffer) -> None: ...
    def transfer_d2h(self, buf: DeviceBuffer, length: int) -> np.ndarray: ...
    def submit(self, instructions: bytes) -> Execution: ...
    def sync(self, execution: Execution) -> None: ...
```

## Targets

| Target | Driver | Status |
|--------|--------|--------|
| PYNQ-Z2 | `pynq.py` | Working |
| Software Sim | `simulator.py` | Planned |
| Alveo/Versal | `xrt.py` | Planned |
| ASIC (GPIO) | `asic_gpio.py` | Planned |
