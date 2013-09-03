#!/usr/bin/env python

import numbers
import numpy as np

from pandas.compat import string_types
from pandas.computation.expr import Expr, _parsers, _ensure_scope
from pandas.computation.engines import _engines


def _check_engine(engine):
    """make sure a valid engine is passed"""
    if engine not in _engines:
        raise KeyError('Invalid engine {0!r} passed, valid engines are'
                       ' {1}'.format(engine, _engines.keys()))
    if engine == 'numexpr':
        try:
            import numexpr
        except ImportError:
            raise ImportError("'numexpr' not found. Cannot use "
                              "engine='numexpr' if 'numexpr' is not installed")


def _check_parser(parser):
    """make sure a valid parser is passed"""
    if parser not in _parsers:
        raise KeyError('Invalid parser {0!r} passed, valid parsers are'
                       ' {1}'.format(parser, _parsers.keys()))


def _check_resolvers(resolvers):
    for resolver in resolvers:
        if not hasattr(resolver, '__getitem__'):
            raise AttributeError('Resolver of type {0!r} must implement '
                                 '__getitem__'.format(type(resolver).__name__))


def eval(expr, parser='pandas', engine='numexpr', truediv=True,
         local_dict=None, global_dict=None, resolvers=None, level=2):
    """Evaluate a Python expression as a string using various backends.

    The following arithmetic operations are supported: ``+``, ``-``, ``*``,
    ``/``, ``**``, ``%``, ``//`` (python engine only) along with the following
    boolean operations: ``|`` (or), ``&`` (and), and ``~`` (not).
    Additionally, the ``'pandas'`` parser allows the use of :keyword:`and`,
    :keyword:`or`, and :keyword:`not` with the same semantics as the
    corresponding bitwise operators.  :class:`~pandas.Series` and
    :class:`~pandas.DataFrame` objects are supported and behave as they would
    with plain ol' Python evaluation.

    Parameters
    ----------
    expr : string
        The expression to evaluate. This string cannot contain any Python
        `statements
        <http://docs.python.org/2/reference/simple_stmts.html#simple-statements>`__,
        only Python `expressions
        <http://docs.python.org/2/reference/simple_stmts.html#expression-statements>`__.
    parser : string, default 'pandas', {'pandas', 'python'}
        The parser to use to construct the syntax tree from the expression. The
        default of ``'pandas'`` parses code slightly different than standard
        Python. Alternatively, you can parse an expression using the
        ``'python'`` parser to retain strict Python semantics.  See the
        :ref:`enhancing performance <enhancingperf.eval>` documentation for
        more details.
    engine : string, default 'numexpr', {'python', 'numexpr'}

        The engine used to evaluate the expression. Supported engines are

        - ``'numexpr'``: This default engine evaluates pandas objects using
                         numexpr for large speed ups in complex expressions
                         with large frames.
        - ``'python'``: Performs operations as if you had ``eval``'d in top
                        level python. This engine is generally not that useful.

        More backends may be available in the future.

    truediv : bool, optional
        Whether to use true division, like in Python >= 3
    local_dict : dict or None, optional
        A dictionary of local variables, taken from locals() by default.
    global_dict : dict or None, optional
        A dictionary of global variables, taken from globals() by default.
    resolvers : list of dict-like or None, optional
        A list of objects implementing the ``__getitem__`` special method that
        you can use to inject an additional collection of namespaces to use for
        variable lookup. For example, this is used in the
        :meth:`~pandas.DataFrame.query` method to inject the
        :attr:`~pandas.DataFrame.index` and :attr:`~pandas.DataFrame.columns`
        variables that refer to their respective :class:`~pandas.DataFrame`
        instance attributes.
    level : int, optional
        The number of prior stack frames to traverse and add to the current
        scope. Most users will **not** need to tinker with this parameter.

    Returns
    -------
    ret : ndarray, numeric scalar, :class:`~pandas.DataFrame`, :class:`~pandas.Series`

    Notes
    -----
    The ``dtype`` of any objects involved in an arithmetic ``%`` operation are
    recursively cast to ``float64``.

    See the :ref:`enhancing performance <enhancingperf.eval>` documentation for
    more details.

    See Also
    --------
    pandas.DataFrame.query
    """
    # make sure we're passed a valid engine
    _check_engine(engine)

    # and parser
    _check_parser(parser)

    # make sure all the resolvers have a __getitem__ method
    if resolvers is not None:
        _check_resolvers(resolvers)

    # get our (possibly passed-in) scope
    env = _ensure_scope(global_dict=global_dict, local_dict=local_dict,
                        resolvers=resolvers, level=level)

    # barf if the user tries to pass something other than a string
    if not isinstance(expr, string_types):
        raise TypeError("eval only accepts strings, you passed an object of "
                        "type {0!r}".format(type(expr).__name__))

    # expressions have an engine, parser, scope and a division flag
    parsed_expr = Expr(expr, engine=engine, parser=parser, env=env,
                       truediv=truediv)

    # construct the engine and evaluate
    eng = _engines[engine]
    eng_inst = eng(parsed_expr)
    ret = eng_inst.evaluate()

    # sanity check for a number if it's a scalar result
    # TODO: eventually take out
    if np.isscalar(ret):
        if not isinstance(ret, (np.number, np.bool_, numbers.Number)):
            raise TypeError('scalar result must be numeric or bool, return'
                            ' type is {0!r}'.format(type(ret).__name__))
    return ret
