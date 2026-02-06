"""
Matrix multiplication kernels for Mini-TPU.

Note: Imports must be inside kernel bodies to enable instruction capture
during compilation. The @kernel decorator patches tpu_txt functions temporarily.
"""

from compiler.kernel import kernel, Param


@kernel
def matmul_4x4(W: Param, X: Param, Z: Param):
    """
    4x4 matrix multiplication kernel.

    Computes: Z = X @ W^T

    Args:
        W: Address of 4x4 weight matrix (16 words)
        X: Address of 4x4 input matrix (16 words)
        Z: Address of 4x4 output matrix (16 words)
    """
    from compiler.tpu_txt import matmul
    matmul(W, X, Z, m=4)


@kernel
def matmul_8x8_tiled(W: Param, X: Param, Z: Param, temp: Param):
    """
    8x8 tiled matrix multiplication using 2x2x2 tile decomposition.

    Computes: Z = X @ W^T

    Both matrices must be stored in tile-major order (4x4 tiles).

    Args:
        W: Address of 8x8 weight matrix in tile-major (64 words)
        X: Address of 8x8 input matrix in tile-major (64 words)
        Z: Address of 8x8 output matrix in tile-major (64 words)
        temp: Address of temporary tile storage (16 words)
    """
    from compiler.tpu_txt import matmul, add
    t2 = 16  # tile size squared (4x4 = 16)

    # Z[i,j] = sum_k(X[i,k] @ W[j,k]^T)
    for i in range(2):
        for j in range(2):
            Z_tile = Z + (i * 2 + j) * t2
            for k in range(2):
                X_tile = X + (i * 2 + k) * t2
                W_tile = W + (j * 2 + k) * t2

                if k == 0:
                    # First: Z[i,j] = X[i,k] @ W[j,k]^T
                    matmul(W_tile, X_tile, Z_tile, m=4)
                else:
                    # Accumulate: Z[i,j] += X[i,k] @ W[j,k]^T
                    matmul(W_tile, X_tile, temp, m=4)
                    for elem in range(t2):
                        add(Z_tile + elem, temp + elem, Z_tile + elem)
