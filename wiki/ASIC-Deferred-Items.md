# ASIC Deferred Items

This page tracks items deferred from Phase 1 tapeout.

## SRAM Macro Banking
- Current: Behavioral SRAM (8192x32)
- Future: Bank 4× IHP 2048x64 macros with address decode logic

## AXI Interface Strategy
- Options: Keep AXI-Stream, simplify to valid/ready, WISBane
- Decision deferred to Phase 2

## Test Infrastructure
- Scan chain insertion (DFT)
- JTAG boundary scan
- BIST for SRAMs

## IO Pad Ring
- IHP IO cell integration
- Padring generation
- ESD protection