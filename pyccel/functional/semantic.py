# coding: utf-8

import os
from os.path import join, dirname

from sympy import Symbol, Lambda, Function, Dummy
from sympy import Tuple, IndexedBase
from sympy.core.function import AppliedUndef
from sympy.core.function import UndefinedFunction
from sympy import Integer, Float
from sympy import sympify
from sympy import FunctionClass


from pyccel.codegen.utilities import random_string
from pyccel.ast.utilities import build_types_decorator
from pyccel.ast.datatypes import Int, Real, Complex, Bool
from pyccel.ast.core import Slice
from pyccel.ast.core import Variable, FunctionDef, Assign, AugAssign
from pyccel.ast.core import Return
from pyccel.ast.basic import Basic

from .datatypes import assign_type, BasicTypeVariable
from .datatypes import TypeVariable, TypeTuple, TypeList
from .glossary import _internal_map_functors
from .glossary import _internal_functors
from .glossary import _internal_zip_functions
from .glossary import _internal_product_functions
from .glossary import _internal_applications
from .glossary import _elemental_math_functions
from .glossary import _math_vector_functions
from .glossary import _math_matrix_functions
from .glossary import _math_functions

#=========================================================================
class Map(Basic):
    """."""

    def __new__( cls, func, target ):

        return Basic.__new__(cls, func, target)

    @property
    def func(self):
        return self._args[0]

    @property
    def target(self):
        return self._args[1]

#=========================================================================
class Zip(Basic):
    def __new__( cls, *args ):
        return Basic.__new__(cls, args)

    @property
    def arguments(self):
        return self._args[0]

    def __len__(self):
        return len(self.arguments)

class Product(Basic):
    def __new__( cls, *args ):
        return Basic.__new__(cls, args)

    @property
    def arguments(self):
        return self._args[0]

    def __len__(self):
        return len(self.arguments)

#=========================================================================
class Reduce(Basic):
    """."""

    def __new__( cls, func, target ):

        return Basic.__new__(cls, func, target)

    @property
    def func(self):
        return self._args[0]

    @property
    def target(self):
        return self._args[1]

#=========================================================================
def sanitize(expr):
    if isinstance(expr, Lambda):
        args = expr.variables
        expr = sanitize(expr.expr)

        return Lambda(args, expr)

    elif isinstance(expr, AppliedUndef):
        name = expr.__class__.__name__

        args = [sanitize(i) for i in expr.args]
        # first argument of Map & Reduce are functions
        if name in _internal_functors:
            first = args[0]
            if isinstance(first, Symbol):
                args[0] = Function(first.name)

        if name in _internal_applications:
            if name in _internal_map_functors:
                return Map(*args)

            elif name == 'reduce':
                return Reduce(*args)

            elif name in _internal_zip_functions:
                return Zip(*args)

            elif name in _internal_product_functions:
                return Product(*args)

            else:
                msg = '{} not available'.format(name)
                raise NotImplementedError(msg)

        else:
            return Function(name)(*args)

    elif isinstance(expr, (int, float, Integer, Float, Symbol)):
        return expr

    else:
        raise TypeError('Not implemented for {}'.format(type(expr)))


#=========================================================================
# TODO add some verifications before starting annotating L
class Parser(object):

    def __init__(self, expr, **kwargs):
        assert(isinstance(expr, Lambda))

        self._expr = expr

        # ...
        self._namespace = {}
        self._d_types   = {}
        self._d_expr    = {}
        self._tag       = random_string( 8 )

        # to store current typed expr
        # this must not be a private variable,
        # in order to modify it on the fly
        self.main = expr
        self.main_type = None
        # ...

        # ... add types for arguments and results
        #     TODO use domain and codomain optional args for functions
        self._typed_functions = kwargs.pop('typed_functions', {})
        for f in self.typed_functions.values():
            type_domain   = assign_type(f.arguments)
            type_codomain = assign_type(f.results)

            self._set_type(f, value=type_domain, domain=True)
            self._set_type(f, value=type_codomain, codomain=True)
        # ...

        # ... default Type
        prefix = kwargs.pop('prefix', 'd') # doubles as default
        dtype     = None
        precision = None
        if prefix == 'i':
            dtype     = Int
            precision = 4

        elif prefix == 's':
            dtype     = Real
            precision = 4

        elif prefix == 'd':
            dtype     = Real
            precision = 8

        elif prefix == 'c':
            dtype     = Complex
            precision = 8

        elif prefix == 'z':
            dtype     = Complex
            precision = 16

        else:
            raise ValueError('Wrong prefix. Available: i, s, d, c, z')

        var = Variable(dtype, 'dummy_' + self.tag, precision=precision)
        self._default_type = TypeVariable(var)
        # ...

        # ... get all functions
        calls = list(expr.atoms(AppliedUndef))
        map_funcs = [i.args[0] for i in calls if i.__class__.__name__ in _internal_map_functors]
        callables = [i.func for i in calls  if not i.__class__.__name__ in _internal_functors]
        functions = list(set(map_funcs + callables))

        for f in functions:
            if str(f) in _elemental_math_functions:
                type_domain   = self.default_type
                type_codomain = self.default_type

                self._set_type(f, value=type_domain, domain=True)
                self._set_type(f, value=type_codomain, codomain=True)

            elif not str(f) in list(_internal_applications) + list(self.typed_functions.keys()):
                raise NotImplementedError('{} not available'.format(str(f)))
        # ...

    @property
    def expr(self):
        return self._expr

    @property
    def typed_functions(self):
        return self._typed_functions

    @property
    def default_type(self):
        return self._default_type

    @property
    def namespace(self):
        return self._namespace

    @property
    def d_types(self):
        return self._d_types

    @property
    def d_expr(self):
        return self._d_expr

    @property
    def tag(self):
        return self._tag

    def inspect(self):
        print('============ types =============')
        print(self.d_types)
        for k,v in self.d_types.items():
            print('  {k} = {v}'.format(k=k, v=v.view()))
        print('================================')

    def _get_label(self, target, domain=False, codomain=False):
        # TODO improve
        if codomain:
            assert(not domain)
            if (isinstance(target, FunctionClass)):
                name = str(target)

            else:
                name = str(target.name)

            return name

        if domain:
            assert(not codomain)
            if (isinstance(target, FunctionClass)):
                name = str(target)

            else:
                name = str(target.name)

            _avail_funcs = list(self.typed_functions.keys()) + _math_functions
            if name in _avail_funcs:
                return name + '_args'

        if isinstance(target, FunctionDef):
            return str(target.name) + '_args'

        elif isinstance(target, UndefinedFunction):
            return str(target)

        elif isinstance(target, Symbol):
            return target.name

        else:
            raise NotImplementedError('for {}'.format(type(target)))

    def _get_type(self, target, domain=False, codomain=False):
        label = self._get_label(target, domain=domain, codomain=codomain)

        if label in self.d_types.keys():
            return self.d_types[label]

        return None

    def _set_type(self, target, value, domain=False, codomain=False):
        label = self._get_label(target, domain=domain, codomain=codomain)

        self.d_types[label] = value
        self._set_expr(value, target)

    def _set_expr(self, t_var, expr):
        self._d_expr[t_var.name] = expr

    def build_namespace(self):
        """builds the namespace from types."""
        raise NotImplementedError('')

    def doit(self, verbose=False):

        # ... compute type
        i_count = 0
        max_count = 2
        while(i_count < max_count and not isinstance(self.main, BasicTypeVariable)):
            if verbose:
                print('----> BEFORE ', self.main)

            self.main = self._visit(self.main)

            if verbose:
                print('<---- AFTER', self.main)

            i_count += 1
        # ...

        return self.main

    def _visit(self, stmt, value=None):

        cls = type(stmt)
        name = cls.__name__

        method = '_visit_{}'.format(name)
        if hasattr(self, method):
            return getattr(self, method)(stmt, value=value)

        elif name in _internal_applications:
#            print('[{}]'.format(name))

            FUNCTION = 'function'
            FUNCTOR  = 'functor'

            if name in ['map', 'pmap', 'tmap', 'ptmap']:
                name = 'map'
                kind = FUNCTOR

            elif name in ['reduce']:
                name = 'reduce'
                kind = FUNCTOR

            elif name in ['zip', 'pzip']:
                name = 'zip'
                kind = FUNCTION

            elif name in ['product', 'pproduct']:
                name = 'product'
                kind = FUNCTION

            else:
                raise NotImplementedError('{}'.format(name))

            pattern = '_visit_{kind}_{name}'
            method  = pattern.format(kind=kind, name=name)
            method = getattr(self, method)

            return method(stmt, value=value)

        # Unknown object, we raise an error.
        raise TypeError('{node} not yet available'.format(node=type(stmt)))

    def _visit_Lambda(self, stmt, value=None):
        # TODO treat args
        self.main = self._visit(stmt.expr)
        if isinstance(self.main, BasicTypeVariable):
            self.main_type = self.main

        return self.main

    def _visit_TypeVariable(self, stmt, value=None):
        return stmt

    def _visit_TypeTuple(self, stmt, value=None):
        return stmt

    def _visit_TypeList(self, stmt, value=None):
        return stmt

    def _visit_Symbol(self, stmt, value=None):
        assert(not( value is None ))
        self._set_type(stmt, value)

    def _visit_functor_map(self, stmt, value=None):
        arguments = stmt.args

        assert( len(arguments) == 2 )
        func   = arguments[0]
        target = arguments[1]

        type_codomain = self._get_type(func, codomain=True)
        type_domain   = self._get_type(func, domain=True)

        if not type_codomain:
            print('> Unable to compute type for {} '.format(stmt))
            raise NotImplementedError('')

        # TODO improve
        if stmt.__class__.__name__ in ['tmap', 'ptmap']:
            # TODO check that rank is the same for all domain
            assert(isinstance(target, AppliedUndef))
            assert(target.__class__.__name__ in ['product', 'pproduct'])

            # we substruct 1 since we use a TypeList
            base_rank = len(target.args) - 1

            type_domain   = assign_type(type_domain, rank=base_rank)
            type_codomain = assign_type(type_codomain, rank=base_rank)

        type_domain   = TypeList(type_domain)
        type_codomain = TypeList(type_codomain)

        self._visit(target, value=type_domain)
        self._set_expr(type_codomain, stmt)

        return type_codomain

    def _visit_function_zip(self, stmt, value=None):
        arguments = stmt.args

        assert(not( value is None ))
        assert(isinstance(value, TypeList))
        assert(len(value.parent.types) == len(arguments))

        if not isinstance(value.parent, TypeTuple):
            msg = '{} not available yet'.format(type(value.parent))
            raise NotImplementedError(msg)

        values = value.parent.types

        for a,t in zip(arguments, values):
            type_domain  = TypeList(t)
            self._visit(a, value=type_domain)

        type_codomain = value

        # update main expression
        self.main = self.main.xreplace({stmt: type_codomain})
        self._set_expr(type_codomain, stmt)

        return type_codomain

    def _visit_function_product(self, stmt, value=None):
        arguments = stmt.args

        assert(not( value is None ))
        assert(isinstance(value, TypeList))
        assert(len(value.parent.types) == len(arguments))

        if not isinstance(value.parent, TypeTuple):
            msg = '{} not available yet'.format(type(value.parent))
            raise NotImplementedError(msg)

        values = value.parent.types

        for a,t in zip(arguments, values):
            type_domain  = TypeList(t)
            self._visit(a, value=type_domain)

        type_codomain = value

        # update main expression
        self.main = self.main.xreplace({stmt: type_codomain})
        self._set_expr(type_codomain, stmt)

        return type_codomain

    def _visit_functor_reduce(self, stmt, value=None):
        arguments = stmt.args

        assert( len(arguments) == 2 )
        op     = arguments[0]
        target = arguments[1]

        # we must first determine the number of arguments
        # TODO must be done in main lambdify:
        #      - we use atoms on AppliedUndef
        #      - then we take those for which we provide python implementations
        #      - then we subtitute the function call by the appropriate one
        #      - and we append its implementation to user_functions
        nargs = len(sanitize(target))
        precision = str(op)[0]
        # TODO check this as in BLAS
        assert( precision in ['i', 's', 'd', 'z', 'c'] )
        print(nargs)

        print('> ', op, type(op))

        import sys; sys.exit(0)
