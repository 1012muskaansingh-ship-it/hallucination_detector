import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph_engine import VerificationEngine
from nlp_extractor import ClaimExtractor, DynamicGraphBuilder

RULES = {("CONTROLS", "ACTIVATES"): "INFLUENCES"}


class VerificationTests(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "ground_truth.txt").read_text(encoding="utf-8")
        entities, edges = DynamicGraphBuilder().extract_triplets_from_text(text)
        self.engine = VerificationEngine(entities, edges)
        self.extractor = ClaimExtractor()

    def verify(self, text):
        c = self.extractor.extract_claim(text)
        return self.engine.verify_claim(c["subject"], c["predicate"], c["object"], RULES)

    def test_direct_supported_claim(self):
        self.assertEqual(self.verify("The server routes traffic.")["verdict"], "VERIFIED")

    def test_wrong_predicate_is_not_proof(self):
        self.assertEqual(self.verify("The firewall routes traffic.")["verdict"], "UNSUPPORTED")

    def test_unknown_entity(self):
        self.assertEqual(self.verify("The quantum router encrypts records.")["verdict"], "UNRESOLVED")

    def test_rule_derivation(self):
        result = self.verify("The server influences database.")
        self.assertEqual(result["verdict"], "VERIFIED")
        self.assertEqual(result["proof_type"], "rule_derivation")

    def test_explicit_contradiction(self):
        self.assertEqual(self.verify("The database routes traffic.")["verdict"], "CONTRADICTED")

    def test_second_direct_fact(self):
        self.assertEqual(self.verify("The database encrypts records.")["verdict"], "VERIFIED")

    def test_entity_exists_but_relation_does_not(self):
        self.assertEqual(self.verify("The server controls database.")["verdict"], "UNSUPPORTED")

    def test_another_direct_fact(self):
        self.assertEqual(self.verify("The admin owns server.")["verdict"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
