# coding: utf-8

from sympy.core.function import Function
from .core import DottedName
from .core import Import
from .core import Range, Len
from .numpyext import Zeros, Ones
from .numpyext import Array ,Shape ,Int, Sum ,Rand

def builtin_function(expr, args=None):
    """Returns a builtin-function call applied to given arguments."""
    if not(isinstance(expr, Function) or isinstance(expr, str)):
        raise TypeError('Expecting a string or a Function class')

    if isinstance(expr, Function):
        name = str(type(expr).__name__)

    if isinstance(expr, str):
        name = expr

    if name == 'range':
        return Range(*args)
    elif name == 'array':
        return Array(*args)
    if name == 'shape':
        return Shape(*args)
    if name == 'int':
        return Int(*args)
    if name == 'len':
        return Len(*args)
    if name == 'sum':
        return Sum(*args)

    return None

def builtin_import(expr):
    """Returns a builtin pyccel-extension function/object from an import."""
    if not isinstance(expr, Import):
        raise TypeError('Expecting an Import expression')

    if expr.source is None:
        return None, None

    source = expr.source
    if isinstance(source, DottedName):
        source = source.name[0]
        #TODO imrove
    if source == 'numpy':
        # TODO improve
        target = str(expr.target[0])
        if target == 'zeros':
            # TODO return as_name and not name
            return target, Zeros

        if target == 'ones':
            # TODO return as_name and not name
            return target, Ones
         
        if target == 'array':
            return target, Array
        
        if target == 'shape':
            return target, Shape
          
        if target == 'int':
            return target, Int
        
        if target == 'sum':
            return target, Sum
        
        if target in ['rand', 'random']:
            return target, Rand

    return None, None


