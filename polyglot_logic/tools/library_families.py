"""AP13 v3.1 static data (doc 09): the algorithm family of common library calls.

Names are the canonical short call names the lowerers produce (module prefixes dropped,
lang_tables.SYNONYMS applied). A library call is reported as LIBRARY, never as a traced
identification.
"""
from lang_tables import LIBRARY

S, Q, N = 'sequence_transformation', 'sequence_query', 'numeric'

LIBRARY_FAMILIES = {
    **{name: [S, 'comparison_sort'] for name in LIBRARY['sort']},
    **{name: [Q, 'target_search', 'interval_halving'] for name in LIBRARY['binary_search']},
    'gcd': [N, 'recurrence', 'modulo_recurrence'],
    'lcm': [N, 'recurrence', 'modulo_recurrence'],
    'factorial': [N, 'recurrence', 'range_accumulation'],
    'isleap': [N, 'predicate'],
    'sum': [Q, 'aggregate', 'gatherer'],
    'max': [Q, 'aggregate', 'most_wanted'], 'min': [Q, 'aggregate', 'most_wanted'],
    'maximum': [Q, 'aggregate', 'most_wanted'], 'minimum': [Q, 'aggregate', 'most_wanted'],
    'index': [Q, 'target_search'], 'indexOf': [Q, 'target_search'], 'elemIndex': [Q, 'target_search'],
    'position': [Q, 'target_search'], 'find': [Q, 'target_search'], 'which': [Q, 'target_search'],
    'reverse': [S, 'uncompared_rearrangement'],
}

# a strong name is the algorithm wherever it is called; a weak name only when it IS the result
STRONG = set(LIBRARY['sort']) | set(LIBRARY['binary_search']) | {'gcd', 'lcm', 'factorial', 'isleap'}
