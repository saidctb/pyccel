# coding: utf-8

import os
from os.path import join, dirname

from sympy import Symbol, Lambda, Function, Dummy
from sympy.core.function import AppliedUndef
from sympy.core.function import UndefinedFunction
from sympy import Integer, Float
from sympy import sympify

from textx.metamodel import metamodel_from_str


from pyccel.codegen.utilities import random_string
from pyccel.ast.core import Variable, FunctionDef
from .ast import Reduce
from .ast import SeqMap, ParMap, BasicMap
from .ast import SeqTensorMap, ParTensorMap, BasicTensorMap
from .ast import SeqZip, SeqProduct
from .ast import ParZip, ParProduct
from .ast import assign_type, BasicTypeVariable, TypeVariable, TypeTuple

_known_functions = {'map':      SeqMap,
                    'pmap':     ParMap,
                    'tmap':     SeqTensorMap,
                    'ptmap':    ParTensorMap,
                    'zip':      SeqZip,
                    'pzip':     ParZip,
                    'product':  SeqProduct,
                    'pproduct': ParProduct,
                    'reduce':   Reduce,
                   }

_functors_registery = ['map', 'pmap', 'tmap', 'ptmap', 'reduce']

_zero  = lambda x: 0
_one   = lambda x: 1
_count = lambda x: len(x)
_base_rank_registery = {'map':      _one,
                        'pmap':     _one,
                        'tmap':     _count,
                        'ptmap':    _count,
                        'zip':      _one,
                        'pzip':     _one,
                        'product':  _one,
                        'pproduct': _one,
                        'reduce':   _zero,
                       }

#==============================================================================
# TODO to be moved in a class
# utilities for semantic analysis
namespace  = {}

# keys = global arguments and functions    ||  values = dictionary for d_var
d_types    = {}
main_expr = None
#==============================================================================

#==============================================================================
# any argument
class AnyArgument(Symbol):
    pass

_ = AnyArgument('_')

#==============================================================================
class NamedAbstraction(object):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        self.abstraction = kwargs.pop('abstraction')

class Abstraction(object):
    def __init__(self, **kwargs):
        self.args = kwargs.pop('args')
        self.expr = kwargs.pop('expr')

class Application(object):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        self.args = kwargs.pop('args')

#==============================================================================
def to_sympy(stmt):

    if isinstance(stmt, NamedAbstraction):
        name = stmt.name
        expr = to_sympy(stmt.abstraction)
        return expr

    elif isinstance(stmt, Abstraction):
        args = [to_sympy(i) for i in stmt.args]
        expr = to_sympy(stmt.expr)

        return Lambda(args, expr)

    elif isinstance(stmt, Application):
        args = [to_sympy(i) for i in stmt.args]
        name = stmt.name

        return Function(name)(*args)

    elif isinstance(stmt, (int, float)):
        return stmt

    elif isinstance(stmt, str):
        if stmt == '_':
            return _

        else:
            return sympify(stmt)

    else:
        raise TypeError('Not implemented for {}'.format(type(stmt)))

#==============================================================================
def sanitize(expr):
    if isinstance(expr, Lambda):
        args = expr.variables
        expr = sanitize(expr.expr)

        return Lambda(args, expr)

    elif isinstance(expr, AppliedUndef):
        name = expr.__class__.__name__

        args = [sanitize(i) for i in expr.args]
        # first argument of Map & Reduce are functions
        if name in _functors_registery:
            first = args[0]
            if isinstance(first, Symbol):
                args[0] = Function(first.name)

        if name in _known_functions.keys():
            return _known_functions[name](*args)

        else:
            return Function(name)(*args)

    elif isinstance(expr, (int, float, Integer, Float, Symbol)):
        return expr

    else:
        raise TypeError('Not implemented for {}'.format(type(expr)))

#==============================================================================
def parse(inputs, debug=False, verbose=False):
    this_folder = dirname(__file__)

    classes = [NamedAbstraction, Abstraction, Application]

    # Get meta-model from language description
    grammar = join(this_folder, 'grammar.tx')

    from textx.metamodel import metamodel_from_file
    meta = metamodel_from_file(grammar, debug=debug, classes=classes)

    # Instantiate model
    if os.path.isfile(inputs):
        ast = meta.model_from_file(inputs)

    else:
        ast = meta.model_from_str(inputs)

    # ...
    expr = to_sympy(ast)
    if verbose:
        print('>>> stage 0 = ', expr)
    # ...

#    # ...
#    expr = sanitize(expr)
#    if verbose:
#        print('>>> stage 1 = ', expr)
#    # ...

    # ...
    if verbose:
        print('')
    # ...

    return expr

#==============================================================================
def _get_key(expr):
    # TODO to be replaced by domain
    if isinstance(expr, FunctionDef):
        return str(expr.name) + '_args'

    elif isinstance(expr, UndefinedFunction):
        return str(expr)

    elif isinstance(expr, Symbol):
        return expr.name

    else:
        raise NotImplementedError('for {}'.format(type(expr)))

#==============================================================================
# TODO add some verifications before starting annotating L
class SemanticParser(object):

    def __init__(self, expr, **kwargs):
        assert(isinstance(expr, Lambda))

        self._expr = expr

        # ...
        self._namespace = {}
        self._d_types   = {}
        self._tag       = random_string( 8 )

        # to store current typed expr
        # this must not be a private variable,
        # in order to modify it on the fly
        self.main = expr
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

#        # ...
#        self.inspect()
#        # ...

    @property
    def expr(self):
        return self._expr

    @property
    def typed_functions(self):
        return self._typed_functions

    @property
    def namespace(self):
        return self._namespace

    @property
    def d_types(self):
        return self._d_types

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
            return str(target.name)

        if domain:
            assert(not codomain)
            name = str(target.name)
            if name in self.typed_functions.keys():
                return name + '_args'

        return _get_key(target)

    def _get_type(self, target, domain=False, codomain=False):
        label = self._get_label(target, domain=domain, codomain=codomain)

        if label in self.d_types.keys():
            return self.d_types[label]

        return None

    def _set_type(self, target, value, domain=False, codomain=False):
        label = self._get_label(target, domain=domain, codomain=codomain)

        self.d_types[label] = value

    def build_namespace(self):
        """builds the namespace from types."""
        raise NotImplementedError('')

    def compute_type(self, verbose=True):

        # ... compute type
        i_count = 0
        max_count = 2
        while(i_count < max_count and not isinstance(self.main, BasicTypeVariable)):
            if verbose:
                print('>>> before ', self.main)

            self.main = self._compute_type(self.main)

            if verbose:
                print('>>> after', self.main)

            i_count += 1
        # ...

        return self.main

    def _compute_type(self, stmt, value=None):

        cls = type(stmt)
        name = cls.__name__

        method = '_compute_type_{}'.format(name)
        if hasattr(self, method):
            return getattr(self, method)(stmt, value=value)

        elif name in _known_functions.keys():
            base_rank = self._preprocess_function(stmt)

            if name in ['map', 'pmap', 'tmap', 'ptmap']:
                name = 'map'

            elif name in ['zip', 'pzip']:
                name = 'zip'

            elif name in ['product', 'pproduct']:
                name = 'product'

            elif name in ['reduce']:
                name = 'reduce'

            else:
                raise NotImplementedError('{}'.format(name))

            method = getattr(self, '_compute_type_function_{}'.format(name))
            arguments = stmt.args
            type_codomain = method(arguments, value=value, base_rank=base_rank)

            return self._postprocess_function(stmt, type_codomain=type_codomain)

        # Unknown object, we raise an error.
        raise TypeError('{node} not yet available'.format(node=type(stmt)))

    def _compute_type_Lambda(self, stmt, value=None):
        # TODO treat args
        self.main = self._compute_type(stmt.expr)
        return self.main

    def _compute_type_TypeVariable(self, stmt, value=None):
        return stmt

    def _compute_type_TypeTuple(self, stmt, value=None):
        return stmt

    def _compute_type_Symbol(self, stmt, value=None):
        assert(not( value is None ))
        self._set_type(stmt, value)

    def _preprocess_function(self, stmt):
        name      = stmt.__class__.__name__
        arguments = stmt.args

        if name in _base_rank_registery.keys():
            base_rank = _base_rank_registery[name](arguments)

        else:
            base_rank = None

        return base_rank

    def _postprocess_function(self, stmt, type_codomain=None):
        if type_codomain is None:
            return self.main

#        print('------')
#        print('> main = ', self.main)
#        print('> stmt = ', stmt)
#        print('> type = ', type_codomain)
#        main = self.main.xreplace({stmt: type_codomain})

        try:
            self.main = self.main.xreplace({stmt: type_codomain})

        except:
            self.inspect()

            print('>>> Something wrong happend')
#            import sys; sys.exit(0)

        return self.main

    def _compute_type_function_map(self, arguments, value=None, base_rank=None):
        assert( len(arguments) == 2 )
        func   = arguments[0]
        target = arguments[1]

        type_codomain = self._get_type(func, codomain=True)
        type_domain   = self._get_type(func, domain=True)

        if not type_codomain:
            print('> Unable to compute type for {} '.format(stmt))

        # TODO may be we should split it here
#        print(type(type_domain))
#        import sys; sys.exit(0)
        type_domain   = assign_type(type_domain, rank=base_rank)
        type_codomain = assign_type(type_codomain, rank=base_rank)

        # no return here
        self._compute_type(target, value=type_domain)

        return type_codomain

    def _compute_type_function_zip(self, arguments, value=None, base_rank=None):
        assert(not( value is None ))

        assert(isinstance(value, TypeTuple))
        assert(len(value) == len(arguments))

        for a,t in zip(arguments, value.types):
            type_domain  = assign_type(t, rank=base_rank)
            self._compute_type(a, value=type_domain)

        type_codomain = value
        return type_codomain

    def _compute_type_function_product(self, arguments, value=None, base_rank=None):
        assert(not( value is None ))

        assert(isinstance(value, TypeTuple))
        assert(len(value) == len(arguments))

        for a,t in zip(arguments, value.types):
            type_domain  = assign_type(t, rank=base_rank)
            self._compute_type(a, value=type_domain)

        type_codomain = value
        return type_codomain

    def _compute_type_function_reduce(self, arguments, value=None, base_rank=None):
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

#    def _annotate(self, stmt):
#
#        cls = type(stmt)
#        name = cls.__name__
#
#        method = '_annotate_{}'.format(name)
#        if hasattr(self, method):
#            return getattr(self, method)(stmt)
#
#        # Unknown object, we raise an error.
#        raise TypeError('{node} not yet available'.format(node=type(stmt)))
#
#    def _annotate_Lambda(self, stmt):
#        return self._annotate(stmt.expr)