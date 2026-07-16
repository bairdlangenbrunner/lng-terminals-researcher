"""schema_constants.py — the canonical GEM-computed / out-of-scope column sets
consolidated out of 3 duplicated copies (completeness_sweep.py, pull_gem_db.py,
build_review_package.py).

build_review_package.py's README sheet enumerates COMPUTED_COLUMNS and
OUT_OF_SCOPE_COLUMNS as two SEPARATE reason groups ("GEM-computed" vs.
"Out-of-scope (frozen 2026)") and unions them into READ_ONLY_COLUMNS — that
only makes sense, and only correctly explains every read-only column exactly
once, if the two sets are disjoint.
"""
import schema_constants as sc


def test_sets_are_non_empty():
    assert sc.COMPUTED_COLUMNS
    assert sc.OUT_OF_SCOPE_COLUMNS
    assert sc.READ_ONLY_COLUMNS


def test_computed_and_out_of_scope_are_disjoint():
    assert sc.COMPUTED_COLUMNS.isdisjoint(sc.OUT_OF_SCOPE_COLUMNS)


def test_read_only_columns_is_exactly_the_union():
    assert sc.READ_ONLY_COLUMNS == sc.COMPUTED_COLUMNS | sc.OUT_OF_SCOPE_COLUMNS
    assert len(sc.READ_ONLY_COLUMNS) == len(sc.COMPUTED_COLUMNS) + len(sc.OUT_OF_SCOPE_COLUMNS)
