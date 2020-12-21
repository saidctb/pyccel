# pylint: disable=missing-function-docstring, missing-module-docstring/
from pyccel.decorators import types

@types('int[:,:]','int[:]')
def mul_by_vector_C(a,b):
    a[:] *= b

@types('int[:,:](order=F)','int[:]')
def mul_by_vector_F(a,b):
    a[:] *= b

@types('int[:,:]')
def mul_by_vector_dim_1_C_C(a):
    import numpy as np
    b = np.array([[1],[2],[3]])
    a[:] *= b

@types('int[:,:]')
def mul_by_vector_dim_1_C_F(a):
    import numpy as np
    b = np.array([[1],[2],[3]], order = 'F')
    a[:] *= b

@types('int[:,:](order=F)')
def mul_by_vector_dim_1_F_C(a):
    import numpy as np
    b = np.array([[1],[2],[3]])
    a[:] *= b

@types('int[:,:](order=F)')
def mul_by_vector_dim_1_F_F(a):
    import numpy as np
    b = np.array([[1],[2],[3]], order = 'F')
    a[:] *= b

@types('int[:,:,:]','int[:,:,:]','int[:,:]','int[:]','int')
def multi_dim_sum(result, a, b, c, d):
    result[:,:,:] = a + b + c + d

@types('int[:,:,:]','int[:,:,:]')
def multi_dim_sum_ones(result, a):
    import numpy as np
    s1,s2,s3 = np.shape(a)
    b = np.empty((1,s2,s3),dtype=int)
    c = np.empty((1, 1,s3),dtype=int)
    b[:,:,:] = a[0]
    c[:,:,:] = a[0,0]
    d = a[0,0,0]
    result[:,:,:] = a + b + c + d

@types('int[:,:]','int[:]')
def multi_expression(a,b):
    import numpy as np
    a[:] *= b
    a[:] *= 2
    b[:] += 4
    a[:] -= b
    a += np.sum(b)
