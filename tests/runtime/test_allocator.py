import unittest
from compiler.runtime.allocator import MemoryAllocator

class TestAllocator(unittest.TestCase):
    def test_contiguous_allocation(self):
        # Verify memory allocator hands out contiguous blocks
        allocator = MemoryAllocator()
        addr1 = allocator.alloc("tensor1", 16)
        addr2 = allocator.alloc("tensor2", 16)
        self.assertEqual(addr1, 0)
        self.assertEqual(addr2, 16)  # Contiguous after first allocation
        
    def test_out_of_memory(self):
        # [PLANNED] Verify OOM exception
        pass
