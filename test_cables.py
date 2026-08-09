import unittest

from knitviz.graph_model import graph_from_pattern
from knitviz.layout import cable_layout, knit_layout, knitting_layout
from knitviz.metrics import count_crossings, crossing_report
from knitviz.patterns import honeycomb_cable, library
from knitviz.stitches import get


class CableLayoutTests(unittest.TestCase):
    def test_standard_cable_tokens(self):
        for token in ("c1b", "c2b", "c3b", "c4b", "c1f", "c2f", "c3f", "c4f"):
            self.assertEqual(get(token).add, 2 * int(token[1:-1]))

    def test_added_patterns_have_valid_initial_layouts(self):
        for pattern in library().values():
            graph = graph_from_pattern(pattern)
            self.assertEqual(count_crossings(graph, knitting_layout(graph)), 0)
        graph = graph_from_pattern(honeycomb_cable())
        report = crossing_report(graph, cable_layout(graph))
        self.assertEqual((report["missing"], report["unexpected"], report["misplaced"]), (0, 0, 0))
        report = crossing_report(graph, knit_layout(graph, iterations=40, seed=1))
        self.assertEqual((report["missing"], report["unexpected"], report["misplaced"]), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
