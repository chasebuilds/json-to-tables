from benchmark.generate import generate
from benchmark.run_benchmark import score


def test_generator_is_seeded() -> None:
    assert generate(1, 30) == generate(1, 30)
    assert generate(1, 30) != generate(2, 30)


def test_small_benchmark_run() -> None:
    s = score(3, 300)
    assert s.found_once == s.leaves
    assert s.missing == s.extra == s.orphans == 0
    assert s.sqlite_rows_match
