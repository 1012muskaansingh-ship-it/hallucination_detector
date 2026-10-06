"""Deterministic graph and matrix engine for hallucination verification.

The engine deliberately separates three ideas:
1. A labeled knowledge graph G=(V,E,P).
2. Predicate-specific adjacency matrices A_p.
3. Explicit inference rules for multi-hop claims.

A graph path by itself is NOT treated as proof of an arbitrary predicate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Edge:
    subject: str
    predicate: str
    object: str


class VerificationEngine:
    def __init__(self, entities: Dict[int, str], edges: Iterable[Tuple[int, int, str]]):
        self.entities = dict(entities)
        self.id_to_idx = {eid: i for i, eid in enumerate(self.entities)}
        self.name_to_id = {name.strip().lower(): eid for eid, name in self.entities.items()}
        self.num_nodes = len(self.entities)

        self.edges: List[Edge] = []
        self.relations: Dict[str, set[Tuple[str, str]]] = {}
        for subject_id, object_id, predicate in edges:
            if subject_id not in self.entities or object_id not in self.entities:
                continue
            subject = self.entities[subject_id]
            obj = self.entities[object_id]
            pred = self.normalize_predicate(predicate)
            edge = Edge(subject, pred, obj)
            self.edges.append(edge)
            self.relations.setdefault(pred, set()).add((subject.lower(), obj.lower()))

    @staticmethod
    def normalize_predicate(predicate: str) -> str:
        return predicate.strip().upper().replace(" ", "_")

    def resolve_entity(self, name: str) -> Optional[str]:
        key = name.strip().lower()
        if key in self.name_to_id:
            return self.entities[self.name_to_id[key]]
        return None

    def predicate_matrix(self, predicate: str) -> List[List[int]]:
        """Return A_p, the binary adjacency matrix for one predicate."""
        pred = self.normalize_predicate(predicate)
        matrix = [[0] * self.num_nodes for _ in range(self.num_nodes)]
        for subject, obj in self.relations.get(pred, set()):
            sid = self.name_to_id[subject]
            oid = self.name_to_id[obj]
            matrix[self.id_to_idx[sid]][self.id_to_idx[oid]] = 1
        return matrix

    @staticmethod
    def multiply_matrices(m1: List[List[int]], m2: List[List[int]]) -> List[List[int]]:
        n = len(m1)
        if n == 0:
            return []
        result = [[0] * n for _ in range(n)]
        for i in range(n):
            for k in range(n):
                if m1[i][k] == 0:
                    continue
                for j in range(n):
                    result[i][j] += m1[i][k] * m2[k][j]
        return result

    def get_matrix_power(self, predicate: str, power: int) -> List[List[int]]:
        if power < 1:
            raise ValueError("Matrix power must be >= 1")
        result = self.predicate_matrix(predicate)
        base = result
        for _ in range(power - 1):
            result = self.multiply_matrices(result, base)
        return result

    def relation_exists(self, subject: str, predicate: str, obj: str) -> bool:
        pred = self.normalize_predicate(predicate)
        return (subject.lower(), obj.lower()) in self.relations.get(pred, set())

    def find_path(self, subject: str, obj: str, predicate: str, max_depth: int = 3) -> List[str]:
        """Find a same-predicate path for explanatory matrix evidence."""
        pred = self.normalize_predicate(predicate)
        adjacency = {}
        for s, o in self.relations.get(pred, set()):
            adjacency.setdefault(s, []).append(o)

        start, target = subject.lower(), obj.lower()
        queue = [(start, [subject])]
        seen = {start}
        while queue:
            current, path = queue.pop(0)
            if len(path) - 1 >= max_depth:
                continue
            for nxt in adjacency.get(current, []):
                if nxt == target:
                    return path + [self._display(nxt)]
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path + [self._display(nxt)]))
        return []

    def _display(self, lowercase_name: str) -> str:
        eid = self.name_to_id[lowercase_name]
        return self.entities[eid]

    def verify_claim(
        self,
        claim_subject: str,
        claim_predicate: str,
        claim_object: str,
        rules: Optional[Dict[Tuple[str, str], str]] = None,
    ) -> dict:
        """Return a deterministic, auditable verdict.

        Verdicts:
        - VERIFIED: exact fact or explicitly permitted rule derivation.
        - CONTRADICTED: an explicit negation/conflicting value is present.
        - UNSUPPORTED: entities exist, but the proposition is not derivable.
        - UNRESOLVED: at least one entity cannot be mapped to the source.
        """
        subject = self.resolve_entity(claim_subject)
        obj = self.resolve_entity(claim_object)
        predicate = self.normalize_predicate(claim_predicate)

        if subject is None or obj is None:
            missing = []
            if subject is None:
                missing.append(claim_subject)
            if obj is None:
                missing.append(claim_object)
            return {
                "verdict": "UNRESOLVED",
                "is_hallucination": None,
                "reason": "Entity not found in the source knowledge graph.",
                "missing_entities": missing,
                "proof_type": "entity_resolution",
            }

        if self.relation_exists(subject, predicate, obj):
            matrix = self.predicate_matrix(predicate)
            si = self.id_to_idx[self.name_to_id[subject.lower()]]
            oi = self.id_to_idx[self.name_to_id[obj.lower()]]
            return {
                "verdict": "VERIFIED",
                "is_hallucination": False,
                "reason": "Exact predicate edge exists in the ground-truth graph.",
                "proof_type": "direct_edge",
                "path": [subject, obj],
                "direct_path_k1": matrix[si][oi],
                "A1": matrix,
                "total_reachability": matrix[si][oi],
            }

        # Explicit contradiction representation: NOT_<PREDICATE> or <PREDICATE>_NOT.
        contradiction_preds = {f"NOT_{predicate}", f"{predicate}_NOT"}
        for cp in contradiction_preds:
            if self.relation_exists(subject, cp, obj):
                return {
                    "verdict": "CONTRADICTED",
                    "is_hallucination": True,
                    "reason": "The source contains an explicit contradictory relation.",
                    "proof_type": "explicit_contradiction",
                }

        # Rule: (predicate_1, predicate_2) -> derived predicate.
        rules = rules or {}
        for (p1, p2), derived in rules.items():
            if self._rule_derives(subject, obj, p1, p2, derived, predicate):
                p1_matrix = self.predicate_matrix(p1)
                p2_matrix = self.predicate_matrix(p2)
                composed = self.boolean_matrix_multiply(p1_matrix, p2_matrix)
                si = self.id_to_idx[self.name_to_id[subject.lower()]]
                oi = self.id_to_idx[self.name_to_id[obj.lower()]]
                if composed[si][oi]:
                    return {
                        "verdict": "VERIFIED",
                        "is_hallucination": False,
                        "reason": f"Claim is derived by explicit rule {p1} AND {p2} -> {derived}.",
                        "proof_type": "rule_derivation",
                        "rule": f"{p1} ∧ {p2} → {derived}",
                        "A1": p1_matrix,
                        "A2": p2_matrix,
                        "composed_matrix": composed,
                        "total_reachability": composed[si][oi],
                        "path": self._rule_path(subject, obj, p1, p2),
                    }

        return {
            "verdict": "UNSUPPORTED",
            "is_hallucination": None,
            "reason": "Both entities exist, but the claimed predicate is not present or derivable under the declared rules.",
            "proof_type": "no_proof",
            "total_reachability": 0,
        }

    def _rule_derives(self, subject, obj, p1, p2, derived, target):
        if self.normalize_predicate(derived) != target:
            return False
        for middle in self.entities.values():
            if self.relation_exists(subject, p1, middle) and self.relation_exists(middle, p2, obj):
                return True
        return False

    def _rule_path(self, subject, obj, p1, p2):
        for middle in self.entities.values():
            if self.relation_exists(subject, p1, middle) and self.relation_exists(middle, p2, obj):
                return [subject, middle, obj]
        return []

    @staticmethod
    def boolean_matrix_multiply(m1, m2):
        n = len(m1)
        result = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                result[i][j] = int(any(m1[i][k] and m2[k][j] for k in range(n)))
        return result
