"""
Pre-built kernels for Mini-TPU.

Provides ready-to-use kernels for common operations like matrix multiplication
and vector operations.

Usage:
    from compiler.kernels import matmul_4x4, vector_add
    from compiler.kernel import KernelLauncher

    launcher = KernelLauncher(tpu)
    compiled = matmul_4x4.compile()
    launcher.launch(compiled, W=0, X=16, Z=32)
"""

from compiler.kernels.matmul import matmul_4x4, matmul_8x8_tiled
from compiler.kernels.vpu import vector_add, vector_sub, vector_mul, vector_relu
from compiler.kernels.vpu_simd import (
    vector_add_simd,
    vector_mul_simd,
    vector_relu_simd,
    vector_scale_simd,
    vector_add_16_simd,
    fused_mlp_layer_simd,
)

__all__ = [
    'matmul_4x4',
    'matmul_8x8_tiled',
    'vector_add',
    'vector_sub',
    'vector_mul',
    'vector_relu',
    'vector_add_simd',
    'vector_mul_simd',
    'vector_relu_simd',
    'vector_scale_simd',
    'vector_add_16_simd',
    'fused_mlp_layer_simd',
]
