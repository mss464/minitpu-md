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
        # Assembler expects: load <addr>, <length>, <values>
        instr = assemble_line("load 0, 2, [1.0, 2.0]")
        self.assertIsNotNone(instr)
