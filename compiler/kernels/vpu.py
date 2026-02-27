"""
Vector Processing Unit (VPU) kernels for Mini-TPU.

Note: Imports must be inside kernel bodies to enable instruction capture
during compilation. The @kernel decorator patches tpu_txt functions temporarily.
"""

from compiler.kernel import kernel, Param


@kernel
def vector_add(A: Param, B: Param, C: Param, n: int = 16):
    """
    Element-wise vector addition.

    Computes: C[i] = A[i] + B[i] for i in 0..n-1

    Args:
        A: Address of first input vector
        B: Address of second input vector
        C: Address of output vector
        n: Number of elements (default 16)
    """
    from compiler.tpu_txt import add
    for i in range(n):
        add(A + i, B + i, C + i)


@kernel
def vector_sub(A: Param, B: Param, C: Param, n: int = 16):
    """
    Element-wise vector subtraction.

    Computes: C[i] = A[i] - B[i] for i in 0..n-1

    Args:
        A: Address of first input vector
        B: Address of second input vector
        C: Address of output vector
        n: Number of elements (default 16)
    """
    from compiler.tpu_txt import sub
    for i in range(n):
        sub(A + i, B + i, C + i)


@kernel
def vector_mul(A: Param, B: Param, C: Param, n: int = 16):
    """
    Element-wise vector multiplication.

    Computes: C[i] = A[i] * B[i] for i in 0..n-1

    Args:
        A: Address of first input vector
        B: Address of second input vector
        C: Address of output vector
        n: Number of elements (default 16)
    """
    from compiler.tpu_txt import mul
    for i in range(n):
        mul(A + i, B + i, C + i)


@kernel
def vector_relu(X: Param, Zero: Param, Y: Param, n: int = 16):
    """
    Element-wise ReLU activation.

    Computes: Y[i] = max(X[i], 0) for i in 0..n-1

    Args:
        X: Address of input vector
        Zero: Address of zero constant (single word)
        Y: Address of output vector
        n: Number of elements (default 16)
    """
    from compiler.tpu_txt import relu
    for i in range(n):
        relu(X + i, Zero, Y + i)
