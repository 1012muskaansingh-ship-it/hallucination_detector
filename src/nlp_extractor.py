"""Lightweight, dependency-free claim/document extractor.

This is intentionally deterministic for the mid-sem prototype. It recognizes
common sentence templates and converts them into (subject, predicate, object)
triples. A spaCy/LLM extractor can be plugged in later without changing the
verification engine.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


class DynamicGraphBuilder:
    PATTERNS = [
        (r"^(.*?)\s+routes\s+(.*?)\.?$", "ROUTES"),
        (r"^(.*?)\s+inspects\s+(.*?)\.?$", "INSPECTS"),
        (r"^(.*?)\s+stores\s+(.*?)\.?$", "STORES"),
        (r"^(.*?)\s+controls\s+(.*?)\.?$", "CONTROLS"),
        (r"^(.*?)\s+activates\s+(.*?)\.?$", "ACTIVATES"),
        (r"^(.*?)\s+is\s+located\s+in\s+(.*?)\.?$", "LOCATED_IN"),
        (r"^(.*?)\s+is\s+not\s+located\s+in\s+(.*?)\.?$", "NOT_LOCATED_IN"),
        (r"^(.*?)\s+owns\s+(.*?)\.?$", "OWNS"),
        (r"^(.*?)\s+works\s+at\s+(.*?)\.?$", "WORKS_AT"),
        (r"^(.*?)\s+causes\s+(.*?)\.?$", "CAUSES"),
        (r"^(.*?)\s+encrypts\s+(.*?)\.?$", "ENCRYPTS"),
        (r"^(.*?)\s+influences\s+(.*?)\.?$", "INFLUENCES"),
        (r"^(.*?)\s+does\s+not\s+route\s+(.*?)\.?$", "NOT_ROUTES"),
        (r"^(.*?)\s+increases\s+(?:the\s+)?risk\s+of\s+(.*?)\.?$", "INCREASES_RISK_OF"),
    ]

    def __init__(self):
        self._next_id = 1

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"\s+", " ", value.strip(" .\t\n"))
        value = re.sub(r"^(?:the|a|an)\s+", "", value, flags=re.IGNORECASE)
        return value

    def extract_triplets_from_text(self, text: str) -> Tuple[Dict[int, str], List[Tuple[int, int, str]]]:
        entities: Dict[int, str] = {}
        edges: List[Tuple[int, int, str]] = []
        ids: Dict[str, int] = {}

        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip()):
            sentence = self._clean(sentence)
            if not sentence:
                continue
            triple = self.extract_triplet(sentence)
            if not triple:
                continue
            subject, predicate, obj = triple
            sid = self._entity_id(subject, ids, entities)
            oid = self._entity_id(obj, ids, entities)
            edges.append((sid, oid, predicate))
        return entities, edges

    def extract_triplet(self, sentence: str):
        s = self._clean(sentence)
        for pattern, predicate in self.PATTERNS:
            match = re.match(pattern, s, flags=re.IGNORECASE)
            if match:
                subject = self._clean(match.group(1))
                obj = self._clean(match.group(2))
                if subject and obj:
                    return subject, predicate, obj
        return None

    def _entity_id(self, name: str, ids: Dict[str, int], entities: Dict[int, str]) -> int:
        key = name.lower()
        if key not in ids:
            ids[key] = self._next_id
            entities[self._next_id] = name
            self._next_id += 1
        return ids[key]


class ClaimExtractor:
    """Extract one deterministic SPO claim using the same patterns as the graph builder."""

    def __init__(self, entity_map=None):
        self.entity_map = entity_map or {}
        self.builder = DynamicGraphBuilder()

    def extract_claim(self, text_claim: str) -> dict:
        triple = self.builder.extract_triplet(text_claim)
        if not triple:
            raise ValueError(f"Could not extract a supported SPO claim from: {text_claim!r}")
        subject, predicate, obj = triple
        return {"subject": subject, "predicate": predicate, "object": obj}

    def extract_triplet(self, text_claim: str) -> dict:
        claim = self.extract_claim(text_claim)
        return {
            "subject_name": claim["subject"],
            "object_name": claim["object"],
            "extracted_predicate": claim["predicate"],
        }
