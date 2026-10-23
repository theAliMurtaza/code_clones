"""Bounded counterexample search for a small, pure Python subset.

Never compiles/executes source, imports modules, or exposes Python objects to code.
Matching samples are evidence only; they do not prove program equivalence.
Unsupported syntax and exhausted budgets produce 'inconclusive', not a match.
"""
import ast
import itertools
import math
import operator
import textwrap
from dataclasses import dataclass


class Unsupported(Exception):
    pass


class Returned(Exception):
    def __init__(self, value):
        self.value = value


BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
          ast.Mod: operator.mod, ast.Pow: operator.pow}
CMPOPS = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
          ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
          ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
BUILTINS = {'range', 'len', 'sum', 'sorted', 'min', 'max', 'abs'}
METHODS = {'append', 'get'}


def bounded(value):
    if type(value) not in (int, float, str, bool, type(None), list, tuple, dict, range):
        raise Unsupported('value type')
    if type(value) is int and value.bit_length() > 128:
        raise Unsupported('integer limit')
    if type(value) is float and not math.isfinite(value):
        raise Unsupported('nonfinite value')
    if isinstance(value, (str, list, tuple, dict, range)) and len(value) > 64:
        raise Unsupported('container limit')
    if isinstance(value, (list, tuple, dict)):
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            if count > 256 or depth > 8:
                raise Unsupported('nested container limit')
            if isinstance(item, dict):
                pending.extend((v, depth + 1) for pair in item.items() for v in pair)
            elif isinstance(item, (list, tuple)):
                pending.extend((v, depth + 1) for v in item)
    return value


class Program:
    def __init__(self, code):
        if len(code) > 131072:
            raise Unsupported('source limit')
        tree = ast.parse(textwrap.dedent(code))
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
            raise Unsupported('one complete function required')
        self.fn = tree.body[0]
        args = self.fn.args
        if (self.fn.decorator_list or args.defaults or args.kw_defaults or args.kwonlyargs
                or args.vararg or args.kwarg):
            raise Unsupported('unsupported signature')
        self.names = [a.arg for a in args.posonlyargs + args.args]
        if not 1 <= len(self.names) <= 2:
            raise Unsupported('arity')
        allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
                   ast.Assign, ast.AugAssign, ast.Expr, ast.If, ast.For, ast.While,
                   ast.Pass, ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Dict,
                   ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.Attribute,
                   ast.Subscript, ast.Slice, ast.IfExp, ast.Load, ast.Store,
                   ast.ListComp, ast.comprehension,
                   ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
                   *BINOPS, *CMPOPS)
        method_targets = {id(node.func) for node in ast.walk(tree)
                          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                          and node.func.attr in METHODS}
        for index, node in enumerate(ast.walk(tree)):
            if index > 2500:
                raise Unsupported('syntax limit')
            if not isinstance(node, allowed):
                raise Unsupported(type(node).__name__)
            if isinstance(node, ast.FunctionDef) and node is not self.fn:
                raise Unsupported('nested function')
            # Python determines local bindings before running the body. Do not
            # accidentally call a builtin when a later assignment shadows it.
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                    and node.id in BUILTINS | {self.fn.name}):
                raise Unsupported('shadowed call binding')
            if isinstance(node, ast.Attribute) and id(node) not in method_targets:
                raise Unsupported('attribute access')
            if isinstance(node, ast.Call):
                named = isinstance(node.func, ast.Name) and node.func.id in BUILTINS | {self.fn.name}
                method = id(node.func) in method_targets
                if not (named or method) or node.keywords:
                    raise Unsupported('call')
        self.steps = 0

    def tick(self):
        self.steps += 1
        if self.steps > 2500:
            raise Unsupported('step limit')

    def call(self, args, depth=0):
        self.tick()
        if depth > 24 or len(args) != len(self.names):
            raise Unsupported('call limit')
        env = dict(zip(self.names, args))
        try:
            self.block(self.fn.body, env, depth)
        except Returned as result:
            return result.value
        return None

    def block(self, nodes, env, depth):
        for node in nodes:
            self.tick()
            if isinstance(node, ast.Return):
                raise Returned(self.expr(node.value, env, depth) if node.value else None)
            if isinstance(node, ast.Assign):
                value = self.expr(node.value, env, depth)
                for target in node.targets:
                    self.assign(target, value, env, depth)
            elif isinstance(node, ast.AugAssign):
                # Resolve the target once, before evaluating the RHS, just as
                # Python does. List += and *= must preserve aliases.
                if isinstance(node.target, ast.Name):
                    container, key = env, node.target.id
                elif isinstance(node.target, ast.Subscript):
                    container = self.expr(node.target.value, env, depth)
                    key = self.expr(node.target.slice, env, depth)
                    if type(container) not in (list, dict):
                        raise TypeError('input does not support item assignment')
                else:
                    raise Unsupported('augmented assignment target')
                previous = container[key]
                value = self.binary(node.op, previous, self.expr(node.value, env, depth))
                if type(previous) is list and isinstance(node.op, (ast.Add, ast.Mult)):
                    previous[:] = value
                    value = previous
                container[key] = value
                bounded(value)
            elif isinstance(node, ast.Expr):
                self.expr(node.value, env, depth)
            elif isinstance(node, ast.If):
                self.block(node.body if self.expr(node.test, env, depth) else node.orelse, env, depth)
            elif isinstance(node, ast.For):
                for item in self.expr(node.iter, env, depth):
                    self.tick()
                    self.assign(node.target, item, env, depth)
                    self.block(node.body, env, depth)
                self.block(node.orelse, env, depth)
            elif isinstance(node, ast.While):
                while self.expr(node.test, env, depth):
                    self.tick()
                    self.block(node.body, env, depth)
                self.block(node.orelse, env, depth)
            elif not isinstance(node, ast.Pass):
                raise Unsupported('statement')

    def assign(self, target, value, env, depth):
        if isinstance(target, ast.Name):
            env[target.id] = bounded(value)
        elif isinstance(target, ast.Subscript):
            container = self.expr(target.value, env, depth)
            if type(container) not in (list, dict):
                # This sample is outside the function's input domain. Other
                # list/dict samples can still reveal observable mutations.
                raise TypeError('input does not support item assignment')
            container[self.expr(target.slice, env, depth)] = bounded(value)
            bounded(container)
        elif isinstance(target, (ast.List, ast.Tuple)):
            if len(target.elts) != len(value):
                raise ValueError('unpacking')
            for item, part in zip(target.elts, value):
                self.assign(item, part, env, depth)
        else:
            raise Unsupported('target')

    def binary(self, op, left, right):
        # Check before operations that could allocate large objects.
        if isinstance(op, ast.Mod) and isinstance(left, str):
            if '%' not in left and type(right) in (int, float, bool):
                # E.g. an even-number filter given a string sample. Python
                # rejects this input; no formatting/allocation is necessary.
                raise TypeError('not all arguments converted during string formatting')
            raise Unsupported('string formatting')
        if isinstance(op, ast.Pow) and (type(right) not in (int, float) or abs(right) > 16):
            raise Unsupported('power limit')
        if isinstance(op, ast.Mult):
            for seq, count in ((left, right), (right, left)):
                if isinstance(seq, (str, list, tuple)) and type(count) is int and len(seq) * max(0, count) > 64:
                    raise Unsupported('repetition limit')
        return bounded(BINOPS[type(op)](left, right))

    def expr(self, node, env, depth):
        self.tick()
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, str, bool, type(None)):
                raise Unsupported('constant')
            return bounded(node.value)
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            result = bounded([self.expr(v, env, depth) for v in node.elts])
            return tuple(result) if isinstance(node, ast.Tuple) else result
        if isinstance(node, ast.Dict):
            return bounded({self.expr(k, env, depth): self.expr(v, env, depth)
                            for k, v in zip(node.keys, node.values)})
        if isinstance(node, ast.BinOp):
            return self.binary(node.op, self.expr(node.left, env, depth), self.expr(node.right, env, depth))
        if isinstance(node, ast.UnaryOp):
            value = self.expr(node.operand, env, depth)
            return bounded({ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}[type(node.op)](value))
        if isinstance(node, ast.BoolOp):
            value = self.expr(node.values[0], env, depth)
            for item in node.values[1:]:
                if (isinstance(node.op, ast.And) and not value) or (isinstance(node.op, ast.Or) and value):
                    break
                value = self.expr(item, env, depth)
            return value
        if isinstance(node, ast.Compare):
            left = self.expr(node.left, env, depth)
            for op, right_node in zip(node.ops, node.comparators):
                right = self.expr(right_node, env, depth)
                if not CMPOPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return self.expr(node.body if self.expr(node.test, env, depth) else node.orelse, env, depth)
        if isinstance(node, ast.Slice):
            return slice(*(self.expr(v, env, depth) if v else None for v in (node.lower, node.upper, node.step)))
        if isinstance(node, ast.Subscript):
            return self.expr(node.value, env, depth)[self.expr(node.slice, env, depth)]
        # Generators are deliberately unsupported: materializing them eagerly
        # would change output types, evaluation order and observable behavior.
        if isinstance(node, ast.ListComp):
            if len(node.generators) != 1 or node.generators[0].is_async:
                raise Unsupported('comprehension')
            gen, result, scope = node.generators[0], [], env.copy()
            for item in self.expr(gen.iter, env, depth):
                self.tick()
                self.assign(gen.target, item, scope, depth)
                if all(self.expr(c, scope, depth) for c in gen.ifs):
                    result.append(self.expr(node.elt, scope, depth))
                    bounded(result)
            return result
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                # Explicit dispatch on interpreter-owned primitive containers;
                # never use getattr or expose arbitrary Python methods/objects.
                receiver = self.expr(node.func.value, env, depth)
                args = [self.expr(v, env, depth) for v in node.args]
                if node.func.attr == 'append':
                    if type(receiver) is not list or len(args) != 1:
                        raise TypeError('append requires a list and one value')
                    if len(receiver) >= 64:
                        raise Unsupported('container limit')
                    receiver.append(args[0])
                    bounded(receiver)
                    return None
                if node.func.attr == 'get':
                    if type(receiver) is not dict or len(args) not in (1, 2):
                        raise TypeError('get requires a dict and one or two values')
                    return bounded(receiver.get(*args))
                raise Unsupported('method')
            args = [self.expr(v, env, depth) for v in node.args]
            name = node.func.id
            if name in env:
                raise Unsupported('shadowed call')
            if name == self.fn.name:
                return self.call(args, depth + 1)
            functions = {'range': range, 'len': len, 'sum': sum, 'sorted': sorted,
                         'min': min, 'max': max, 'abs': abs}
            return bounded(functions[name](*args))
        raise Unsupported('expression')


@dataclass(frozen=True)
class Evidence:
    status: str
    checked: int = 0
    reason: str = ''
    diverse_outputs: int = 0


def _samples(arity):
    values = [0, 1, 2, 3, 5, 8, -1, -3, [], [0], [1, 2, 2],
              [-2, 0, 3], [3, 1, 2], [1, 1, 1], '', 'aba', 'abc']
    if arity == 1:
        return [(v,) for v in values]
    return list(itertools.product([0, 1, 2, -1, 3], repeat=2))


def probe(code):
    """Evaluate a fragment once per analysis; only interpreter-owned inputs exist."""
    import copy
    try:
        program = Program(code)
    except (Unsupported, SyntaxError, ValueError, RecursionError):
        return None
    outcomes = {}
    for index, args in enumerate(_samples(len(program.names))):
        program.steps = 0
        try:
            inputs = copy.deepcopy(args)
            result = bounded(program.call(inputs))
            # Include side effects on mutable arguments in the comparison.
            outcomes[index] = bounded((result, inputs))
        except Unsupported:
            return None
        except (TypeError, ValueError, KeyError, IndexError, ZeroDivisionError, OverflowError):
            continue  # Outside this function's accepted input domain.
        except RecursionError:
            return None
    return len(program.names), outcomes


def compare_probes(a, b):
    if a is None or b is None or a[0] != b[0]:
        return Evidence('inconclusive')
    shared = sorted(a[1].keys() & b[1].keys())
    for count, key in enumerate(shared, 1):
        left, right = a[1][key], b[1][key]
        if type(left[0]) != type(right[0]) or left != right:
            return Evidence('different', count, 'Different outputs for the same bounded test input')
    if not shared and len(a[1]) >= 3 and len(b[1]) >= 3:
        return Evidence('different', 0, 'Disjoint input domains in bounded checks')
    distinct = len({repr(a[1][key][0]) for key in shared})
    return Evidence('consistent' if len(shared) >= 3 else 'inconclusive', len(shared),
                    diverse_outputs=distinct)
