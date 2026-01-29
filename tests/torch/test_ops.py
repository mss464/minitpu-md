import unittest
from torch.ops import matmul, relu

class TestTorchOps(unittest.TestCase):
    def test_matmul_op(self):
        # This will test the high-level API wrapper
        # Should verify that it generates correct IR calls
        pass
