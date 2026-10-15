"""AP13 static language data. Tables only: no logic beyond tiny lookups.

Every lowerer reads these tables, so a new language is mostly a new table.
Roles are tree-sitter field names, or '#N' for the N-th named child.
"""
from __future__ import annotations

EXTENSIONS = {
    '.py': 'python', '.rs': 'rust', '.java': 'java', '.c': 'c', '.h': 'c',
    '.r': 'r', '.hs': 'haskell', '.lisp': 'commonlisp', '.lsp': 'commonlisp',
    '.cl': 'commonlisp', '.pl': 'prolog', '.pro': 'prolog',
}
LANGUAGES = ('python', 'rust', 'java', 'c', 'r', 'haskell', 'commonlisp', 'prolog')
TREE_SITTER_LANGUAGES = tuple(x for x in LANGUAGES if x != 'prolog')

# Source spelling -> canonical operator name (shared by all languages).
OPERATORS = {
    '>': 'gt', '<': 'lt', '>=': 'ge', '<=': 'le', '=<': 'le',
    '==': 'eq', '=:=': 'eq', '=': 'eq', '!=': 'ne', '/=': 'ne', '=\\=': 'ne',
    '+': 'add', '-': 'sub', '*': 'mul', '//': 'div', '%/%': 'div', 'div': 'div',
    'quot': 'div', 'floor': 'div', '%': 'mod', 'mod': 'mod', 'rem': 'mod',
    '%%': 'mod', '/': 'fdiv', '&&': 'and', 'and': 'and', '||': 'or', 'or': 'or',
    '&': 'and', '|': 'or', '!': 'not', 'not': 'not', '1+': 'inc', '1-': 'dec',
    '>>': 'shr', '>>>': 'shr', 'ash': 'shl',
}
# Constructors that only wrap a result ("found" markers): transparent (Some x, Just x, Ok x).
WRAPPERS = {'Some', 'Just', 'Ok'}
# Languages whose '/' on integers is integer division.
INT_SLASH = {'c', 'java', 'rust', 'commonlisp'}
AUGMENTED = {'+=': 'add', '-=': 'sub', '*=': 'mul', '/=': 'div', '//=': 'div', '%=': 'mod'}
# Calls that only measure a sequence (P7 in doc 02).
LENGTH_CALLS = {'len', 'length', 'size', 'count', 'nrow'}
# Calls that exchange two positions of a sequence: (sequence, i, j).
SWAP_CALLS = {'swap'}

# Imperative node table: node type -> (kind, {role: field or '#N'}).
_COMMON_EXPR = {
    'identifier': ('ident', {}),
    'parenthesized_expression': ('paren', {'inner': '#0'}),
    'true': ('bool', {}), 'false': ('bool', {}),
}
SPEC = {
    'python': {
        **_COMMON_EXPR,
        'module': ('block', {}), 'block': ('block', {}),
        'function_definition': ('function', {'name': 'name', 'params': 'parameters', 'body': 'body'}),
        'class_definition': ('class', {'name': 'name', 'body': 'body'}),
        'decorated_definition': ('decorated', {'inner': 'definition'}),
        'for_statement': ('for_range', {'var': 'left', 'iter': 'right', 'body': 'body'}),
        'while_statement': ('while', {'cond': 'condition', 'body': 'body'}),
        'if_statement': ('if', {'cond': 'condition', 'then': 'consequence', 'alt': 'alternative'}),
        'elif_clause': ('if', {'cond': 'condition', 'then': 'consequence'}),
        'else_clause': ('else', {'body': 'body'}),
        'expression_statement': ('expr_stmt', {'inner': '#0'}),
        'assignment': ('assign', {'left': 'left', 'right': 'right'}),
        'augmented_assignment': ('aug_assign', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'return_statement': ('return', {'value': '#0'}),
        'binary_operator': ('binary', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'boolean_operator': ('binary', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'comparison_operator': ('compare', {'left': '#0', 'op': 'operators', 'right': '#1'}),
        'not_operator': ('not', {'arg': 'argument'}),
        'unary_operator': ('unary', {'op': 'operator', 'arg': 'argument'}),
        'subscript': ('index', {'seq': 'value', 'idx': 'subscript'}),
        'integer': ('int', {}),
        'call': ('call', {'fn': 'function', 'args': 'arguments'}),
        'attribute': ('field', {'obj': 'object', 'field': 'attribute'}),
        'pattern_list': ('tuple', {}), 'expression_list': ('tuple', {}),
        'tuple': ('tuple', {}), 'tuple_pattern': ('tuple', {}),
    },
    'rust': {
        **_COMMON_EXPR,
        'source_file': ('block', {}), 'block': ('block', {}),
        'function_item': ('function', {'name': 'name', 'params': 'parameters', 'body': 'body'}),
        'impl_item': ('class', {'name': 'type', 'body': 'body'}),
        'declaration_list': ('block', {}),
        'for_expression': ('for_range', {'var': 'pattern', 'iter': 'value', 'body': 'body'}),
        'while_expression': ('while', {'cond': 'condition', 'body': 'body'}),
        'if_expression': ('if', {'cond': 'condition', 'then': 'consequence', 'alt': 'alternative'}),
        'else_clause': ('else', {'body': '#0'}),
        'expression_statement': ('expr_stmt', {'inner': '#0'}),
        'let_declaration': ('assign', {'left': 'pattern', 'right': 'value'}),
        'assignment_expression': ('assign', {'left': 'left', 'right': 'right'}),
        'compound_assignment_expr': ('aug_assign', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'return_expression': ('return', {'value': '#0'}),
        'binary_expression': ('binary', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'unary_expression': ('unary', {'arg': '#0'}),
        'index_expression': ('index', {'seq': '#0', 'idx': '#1'}),
        'type_cast_expression': ('paren', {'inner': 'value'}),
        'reference_expression': ('paren', {'inner': 'value'}),
        'integer_literal': ('int', {}), 'boolean_literal': ('bool', {}),
        'call_expression': ('call', {'fn': 'function', 'args': 'arguments'}),
        'field_expression': ('field', {'obj': 'value', 'field': 'field'}),
        'tuple_expression': ('tuple', {}), 'tuple_pattern': ('tuple', {}),
        'mut_pattern': ('paren', {'inner': '#0'}),
    },
    'java': {
        **_COMMON_EXPR,
        'program': ('block', {}), 'block': ('block', {}), 'class_body': ('block', {}),
        'class_declaration': ('class', {'name': 'name', 'body': 'body'}),
        'method_declaration': ('function', {'name': 'name', 'params': 'parameters', 'body': 'body'}),
        'for_statement': ('c_for', {'init': 'init', 'cond': 'condition', 'update': 'update', 'body': 'body'}),
        'enhanced_for_statement': ('for_range', {'var': 'name', 'iter': 'value', 'body': 'body'}),
        'while_statement': ('while', {'cond': 'condition', 'body': 'body'}),
        'do_statement': ('do_while', {'cond': 'condition', 'body': 'body'}),
        'if_statement': ('if', {'cond': 'condition', 'then': 'consequence', 'alt': 'alternative'}),
        'expression_statement': ('expr_stmt', {'inner': '#0'}),
        'local_variable_declaration': ('decl', {'declarator': 'declarator'}),
        'variable_declarator': ('assign', {'left': 'name', 'right': 'value'}),
        'assignment_expression': ('assign', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'update_expression': ('update', {'arg': '#0'}),
        'return_statement': ('return', {'value': '#0'}),
        'binary_expression': ('binary', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'unary_expression': ('unary', {'op': 'operator', 'arg': 'operand'}),
        'array_access': ('index', {'seq': 'array', 'idx': 'index'}),
        'decimal_integer_literal': ('int', {}),
        'method_invocation': ('method', {'obj': 'object', 'name': 'name', 'args': 'arguments'}),
        'field_access': ('field', {'obj': 'object', 'field': 'field'}),
        'cast_expression': ('paren', {'inner': 'value'}),
    },
    'c': {
        **_COMMON_EXPR,
        'translation_unit': ('block', {}), 'compound_statement': ('block', {}),
        'function_definition': ('function', {'name': 'declarator', 'params': 'declarator', 'body': 'body'}),
        'for_statement': ('c_for', {'init': 'initializer', 'cond': 'condition', 'update': 'update', 'body': 'body'}),
        'while_statement': ('while', {'cond': 'condition', 'body': 'body'}),
        'do_statement': ('do_while', {'cond': 'condition', 'body': 'body'}),
        'if_statement': ('if', {'cond': 'condition', 'then': 'consequence', 'alt': 'alternative'}),
        'else_clause': ('else', {'body': '#0'}),
        'expression_statement': ('expr_stmt', {'inner': '#0'}),
        'declaration': ('decl', {'declarator': 'declarator'}),
        'init_declarator': ('assign', {'left': 'declarator', 'right': 'value'}),
        'assignment_expression': ('assign', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'update_expression': ('update', {'arg': 'argument'}),
        'return_statement': ('return', {'value': '#0'}),
        'binary_expression': ('binary', {'left': 'left', 'op': 'operator', 'right': 'right'}),
        'unary_expression': ('unary', {'op': 'operator', 'arg': 'argument'}),
        'subscript_expression': ('index', {'seq': 'argument', 'idx': 'index'}),
        'number_literal': ('int', {}),
        'call_expression': ('call', {'fn': 'function', 'args': 'arguments'}),
        'field_expression': ('field', {'obj': 'argument', 'field': 'field'}),
        'cast_expression': ('paren', {'inner': 'value'}),
        'pointer_declarator': ('paren', {'inner': 'declarator'}),
    },
    'r': {
        **_COMMON_EXPR,
        'program': ('block', {}), 'braced_expression': ('block', {}),
        'function_definition': ('function', {'params': 'parameters', 'body': 'body'}),
        'for_statement': ('for_range', {'var': 'variable', 'iter': 'sequence', 'body': 'body'}),
        'while_statement': ('while', {'cond': 'condition', 'body': 'body'}),
        'repeat_statement': ('do_while', {'body': 'body'}),
        'if_statement': ('if', {'cond': 'condition', 'then': 'consequence', 'alt': 'alternative'}),
        'binary_operator': ('binary', {'left': 'lhs', 'op': 'operator', 'right': 'rhs'}),
        'unary_operator': ('unary', {'op': 'operator', 'arg': 'rhs'}),
        'parenthesized_expression': ('paren', {'inner': 'body'}),
        'subset': ('index', {'seq': 'function', 'idx': 'arguments'}),
        'integer': ('int', {}), 'float': ('int', {}),
        'call': ('call', {'fn': 'function', 'args': 'arguments'}),
    },
}
# R assignment is a binary operator.
R_ASSIGN = {'<-', '=', '<<-'}
R_ASSIGN_RIGHT = {'->', '->>'}
# Statement kinds that may implicitly return the function's last expression (P5).
IMPLICIT_RETURN = {'rust', 'r'}

# Haskell 2010 Report fixities for the shunting-yard rebuild (P1).
HASKELL_FIXITY = {
    '!': ('l', 9), '.': ('r', 9), '*': ('l', 7), '/': ('l', 7), 'div': ('l', 7),
    'mod': ('l', 7), 'quot': ('l', 7), 'rem': ('l', 7), '+': ('l', 6), '-': ('l', 6),
    ':': ('r', 5), '++': ('r', 5), '==': ('n', 4), '/=': ('n', 4), '<': ('n', 4),
    '<=': ('n', 4), '>': ('n', 4), '>=': ('n', 4), '&&': ('r', 3), '||': ('r', 2),
    '$': ('r', 0),
}
HASKELL_INDEX = {'!', '!!'}

# Common Lisp operators that are expressions, not statements.
LISP_COMPARE = {'>', '<', '>=', '<=', '=', '/='}
LISP_ARITH = {'+', '-', '*', '/', 'floor', 'mod', 'rem', 'truncate'}

# ----- AP13 v2 (doc 04) -------------------------------------------------------
# Library calls with one meaning across languages -> one canonical name (G7).
SYNONYMS = {
    'ord': 'ord', 'fromEnum': 'ord', 'char-code': 'ord', 'charCodeAt': 'ord', 'utf8ToInt': 'ord',
    'chr': 'chr', 'toEnum': 'chr', 'code-char': 'chr', 'intToUtf8': 'chr',
    'append': 'append', 'push': 'append', 'push_back': 'append', 'add': 'append',
    'vector-push-extend': 'append',
    'abs': 'abs', 'sqrt': 'sqrt', 'isqrt': 'sqrt', 'max': 'max', 'min': 'min',
    'reverse': 'reverse', 'rev': 'reverse', 'nreverse': 'reverse',
}
# Statements that carry no algorithmic logic (docstrings, imports, declarations).
IGNORED_STATEMENTS = {
    'pass_statement', 'import_statement', 'import_from_statement', 'global_statement',
    'nonlocal_statement', 'future_import_statement', 'string', 'comment', 'line_comment',
    'block_comment', 'empty_statement', 'ellipsis', 'preproc_include', 'use_declaration',
}
# Early exits: after `if c: <exit>` the rest of the block runs only when c is false (G6).
EXIT_STATEMENTS = {
    'return_statement', 'return_expression', 'raise_statement', 'throw_statement',
    'break_statement', 'break_expression', 'continue_statement', 'continue_expression',
    'break', 'next',
}
# Higher-order folds: f(acc, element) over a sequence with an initial value (G5).
FOLDS = {'foldl', "foldl'", 'foldr', 'reduce', 'Reduce', 'foldl1', 'fold'}

# ----- library / idiom identification (doc 07, part 3) ------------------------------
# A standard-library call is reported as "LIBRARY: <algorithm>", never as a traced match.
# Names are the canonical short call names produced by the lowerers (module prefixes dropped).
LIBRARY = {
    'gcd': {'gcd'},
    'lcm': {'lcm'},
    'factorial': {'factorial'},
    'sort': {'sorted', 'sort', 'sort_unstable', 'sort_by', 'sortBy', 'sortOn', 'qsort', 'msort',
             'predsort', 'stable-sort', 'order'},
    'binary_search': {'bisect_left', 'bisect_right', 'bisect', 'binary_search', 'binarySearch', 'bsearch'},
    'reverse': {'reverse', 'reversed'},
}
# Idioms: product of the range 1..n is the factorial.
PRODUCT_CALLS = {'product', 'prod'}
RANGE_CALLS = {'range', 'seq_len', 'seq'}
