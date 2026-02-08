import numpy as np


instruction_log = []

def log_instruction(op, *operands):
  instruction = f"{op} {', '.join(map(str, operands))}"
  instruction_log.append(instruction)

def matmul(W, X, Z, m=4):
    """
    Given two mxm input matrices stored contiguously in memory starting
    at address W and address X, performs X ⋅ W^T and stores data contigously
    in memory starting at address Z.

    *Z = *X ⋅ (*W)^T

    """
    log_instruction("matmul", W, X, Z)

def load(start_addr, np_array):
    """
    Loads data in np_array contiguously in memory starting at "start_addr"
    """
    # Convert to numpy array
    if not isinstance(np_array, np.ndarray):
        np_array = np.array(np_array, dtype=np.float32)

    # Flatten 2D or 3D arrays → always 1D
    flat = np_array.astype(np.float32).reshape(-1)

    length = flat.size

    value_literal = flat.tolist()

    log_instruction("load", start_addr, length, value_literal)

def store(start_addr, length, name):
    """
    Request "length" number of words to be read contigously from memory starting at
    "start_addr" and prints data under label "name"
    """
    log_instruction("store", start_addr, length, name)
    
def add(X, Y, Z):
    """
    Adds data stored at address X and address Y and stores result in address Z
    *Z = *X + *Y
    """
    log_instruction("add", X, Y, Z)

def sub(X, Y, Z):
    """
    Subtracts data stored at address Y from data stored at address X and stores result in address Z
    *Z = *X - *Y
    """
    log_instruction("sub", X, Y, Z)

def mul(X, Y, Z):
    """
    Multiplies data stored at address X and address Y and stores result in address Z
    *Z = (*X) * (*Y)
    """
    log_instruction("mul", X, Y, Z)

def relu(X, Zero_addr, Y):
    """
    Applies relu function on data stored at address X and stores result in address Y
    *Y = relu(*X)
    """
    log_instruction("relu", X, Zero_addr, Y)

def relu_derivative(X, Zero_addr, Y):
    """
    Applies relu derivative function on data stored at address X and stores result in address Y
    *Y = relu'(*X)
    """
    log_instruction("relu_derivative", X, Zero_addr, Y)

def get_instruction_log():
   return instruction_log


def clear_instruction_log():
    """Clear the instruction log for a fresh compilation."""
    instruction_log.clear()


def vload(vreg: int, addr: int):
    """Load 8 FP32 values from BRAM to vector register.

    Args:
        vreg: Destination vector register (0-7)
        addr: BRAM start address
    """
    log_instruction("vload", vreg, addr)


def vstore(vreg: int, addr: int):
    """Store 8 FP32 values from vector register to BRAM.

    Args:
        vreg: Source vector register (0-7)
        addr: BRAM destination address
    """
    log_instruction("vstore", vreg, addr)


def vadd(vreg_dst: int, vreg_a: int, vreg_b: int, scalar: bool = False):
    """Vector addition: vreg_dst[i] = vreg_a[i] + vreg_b[i].

    Args:
        vreg_dst: Destination register
        vreg_a: Source register A
        vreg_b: Source register B (or scalar if scalar=True)
        scalar: If True, broadcast vreg_b[0] to all lanes
    """
    log_instruction("vadd", vreg_dst, vreg_a, vreg_b, scalar)


def vsub(vreg_dst: int, vreg_a: int, vreg_b: int, scalar: bool = False):
    """Vector subtraction: vreg_dst[i] = vreg_a[i] - vreg_b[i]."""
    log_instruction("vsub", vreg_dst, vreg_a, vreg_b, scalar)


def vmul(vreg_dst: int, vreg_a: int, vreg_b: int, scalar: bool = False):
    """Vector multiplication: vreg_dst[i] = vreg_a[i] * vreg_b[i]."""
    log_instruction("vmul", vreg_dst, vreg_a, vreg_b, scalar)


def vrelu(vreg_dst: int, vreg_src: int):
    """Vector ReLU: vreg_dst[i] = max(vreg_src[i], 0)."""
    log_instruction("vrelu", vreg_dst, vreg_src)


def vmax(vreg_dst: int, vreg_a: int, vreg_b: int):
    """Vector max: vreg_dst[i] = max(vreg_a[i], vreg_b[i])."""
    log_instruction("vmax", vreg_dst, vreg_a, vreg_b)


def vmin(vreg_dst: int, vreg_a: int, vreg_b: int):
    """Vector min: vreg_dst[i] = min(vreg_a[i], vreg_b[i])."""
    log_instruction("vmin", vreg_dst, vreg_a, vreg_b)


def tiled_matmul(W_addr, X_addr, Z_addr, M, N, K, tile_size=4, temp_addr=None, allocator=None):
    """
    Performs tiled matrix multiplication for matrices larger than hardware tile size.

    Computes Z = X @ W^T where:
    - X is M x K matrix at X_addr
    - W is N x K matrix at W_addr
    - Z is M x N matrix at Z_addr

    Args:
        W_addr: Base address of weight matrix W (N x K, row-major, stored as tiles)
        X_addr: Base address of input matrix X (M x K, row-major, stored as tiles)
        Z_addr: Base address of output matrix Z (M x N, row-major, stored as tiles)
        M: Number of rows in X and Z
        N: Number of rows in W (columns in Z)
        K: Number of columns in X and W
        tile_size: Hardware tile size (default 4)
        temp_addr: Address for temporary tile storage (tile_size^2 words)
                   If None and allocator provided, will allocate automatically
        allocator: Optional MemoryAllocator for temp buffer allocation

    Raises:
        ValueError: If dimensions are not multiples of tile_size

    Note:
        Matrices must be stored in tile-major order:
        For an MxN matrix with tile_size t, tiles are stored as:
        [tile(0,0), tile(0,1), ..., tile(0,N/t-1), tile(1,0), ...]
        Each tile is stored row-major within the tile.
    """
    t = tile_size
    t2 = t * t  # words per tile

    # Validate dimensions
    if M % t != 0:
        raise ValueError(f"M={M} must be multiple of tile_size={t}")
    if N % t != 0:
        raise ValueError(f"N={N} must be multiple of tile_size={t}")
    if K % t != 0:
        raise ValueError(f"K={K} must be multiple of tile_size={t}")

    M_tiles = M // t  # Number of tile rows in X/Z
    N_tiles = N // t  # Number of tile rows in W / tile cols in Z
    K_tiles = K // t  # Number of tile cols in X and W

    # Handle temp buffer
    if temp_addr is None:
        if allocator is not None:
            temp_addr = allocator.alloc("_tiled_matmul_temp", t2)
        else:
            raise ValueError("Must provide temp_addr or allocator for tiled_matmul")

    # Triple nested loop over tiles
    # Z[i,j] = sum_k( X[i,k] @ W[j,k]^T )
    for i in range(M_tiles):
        for j in range(N_tiles):
            # Output tile address: Z[i,j]
            Z_tile_addr = Z_addr + (i * N_tiles + j) * t2

            for k in range(K_tiles):
                # Input tile addresses
                X_tile_addr = X_addr + (i * K_tiles + k) * t2  # X[i,k]
                W_tile_addr = W_addr + (j * K_tiles + k) * t2  # W[j,k]

                if k == 0:
                    # First iteration: Z[i,j] = X[i,k] @ W[j,k]^T
                    matmul(W_tile_addr, X_tile_addr, Z_tile_addr, m=t)
                else:
                    # Subsequent iterations: Z[i,j] += X[i,k] @ W[j,k]^T
                    # Compute temp = X[i,k] @ W[j,k]^T
                    matmul(W_tile_addr, X_tile_addr, temp_addr, m=t)
                    # Accumulate: Z[i,j] += temp (element-wise)
                    for elem in range(t2):
                        add(Z_tile_addr + elem, temp_addr + elem, Z_tile_addr + elem)

    # Free temp buffer if we allocated it
    if allocator is not None:
        allocator.free("_tiled_matmul_temp")

