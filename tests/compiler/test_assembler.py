import unittest
from compiler.assembler import assemble_line

class TestAssembler(unittest.TestCase):
    def test_matmul_encoding(self):
        # Example test case for MATMUL opcode
        # MATMUL: 4 (0100) | addr_a: 1 | addr_b: 17 | addr_out: 33
        instr = assemble_line("matmul 1 17 33")
        self.assertIsNotNone(instr)
        # Expected hex logic here...

    def test_load_encoding(self):
        # load instruction populates LOADS list, doesn't generate instruction word
        # Import the module to access the LOADS list
        from compiler import assembler
        assembler.LOADS = []  # Reset
        instr = assemble_line("load 0, 2, [1.0, 2.0]")
        # load returns None (no instruction word), but populates LOADS
        self.assertIsNone(instr)
        self.assertEqual(len(assembler.LOADS), 1)
        self.assertEqual(assembler.LOADS[0], (0, 2, [1.0, 2.0]))
