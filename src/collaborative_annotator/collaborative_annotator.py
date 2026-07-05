import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass
class OntologyTerm:
    iri: str
    label: str
    term_type: str
    description: str = ""


@dataclass
class AnnotationCandidate:
    annotated_text: str
    entity: str
    label: str
    iri: str
    score: float
    votes: int
    evidence: List[str]


@dataclass
class InstructionTunedCommitteeMember:
    name: str
    agent: Any
    instruction: str


DEFAULT_INSTRUCTION_PROFILES = [
    "Prioritize exact ontology label matches and reject speculative matches.",
    "Prioritize semantic paraphrase matching using the candidate descriptions.",
    "Prioritize domain-specific Darwin Core terminology consistency.",
    "Prioritize high precision: return fewer labels unless strongly supported.",
    "Prioritize high recall: include plausible labels with calibrated scores.",
    "Prioritize contradictory-checking: penalize labels not supported by evidence.",
]


def _extract_json_object(raw_text: str) -> Dict:
    text = (raw_text or "").strip()
    if not text:
        return {}

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}

    return {}


class TTLConceptCatalog:
    def __init__(self, class_terms: Sequence[OntologyTerm], property_terms: Sequence[OntologyTerm]):
        self.class_terms = list(class_terms)
        self.property_terms = list(property_terms)

    @classmethod
    def from_ttl_file(cls, ttl_path: str) -> "TTLConceptCatalog":
        text = Path(ttl_path).read_text(encoding="utf-8")

        class_terms: List[OntologyTerm] = []
        property_terms: List[OntologyTerm] = []

        blocks = re.findall(r"(?ms)^###\s+[^\n]+\n(.+?)(?=\n###\s+|\Z)", text)
        for block in blocks:
            subject_match = re.search(r"^\s*(<[^>]+>|[A-Za-z_][\w\-]*:[\w\-]+)", block)
            if not subject_match:
                continue

            subject = subject_match.group(1).strip()
            iri = subject[1:-1] if subject.startswith("<") and subject.endswith(">") else subject

            label = _first_literal(block, [r"rdfs:label\s+\"([^\"]+)\""])
            if not label:
                label = _first_literal(
                    block,
                    [
                        r"ex:matchedTermLabel\s+\"([^\"]+)\"",
                        r"ex:dwcPropertyLabel\s+\"([^\"]+)\"",
                        r"ex:dwcClassLabel\s+\"([^\"]+)\"",
                    ],
                )
            if not label:
                continue

            description = _first_literal(
                block,
                [
                    r"skos:definition\s+\"([^\"]+)\"",
                    r"dcterms:description\s+\"([^\"]+)\"",
                    r"rdfs:comment\s+\"([^\"]+)\"",
                ],
            )

            term = OntologyTerm(
                iri=iri,
                label=label.strip(),
                term_type=_guess_term_type(block),
                description=(description or "").strip(),
            )

            if term.term_type == "class":
                class_terms.append(term)
            elif term.term_type == "property":
                property_terms.append(term)

        return cls(class_terms=class_terms, property_terms=property_terms)


def _first_literal(block: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, block)
        if match:
            return match.group(1)
    return ""


def _guess_term_type(block: str) -> str:
    if "rdf:type owl:Class" in block:
        return "class"
    if (
        "rdf:type owl:ObjectProperty" in block
        or "rdf:type owl:DatatypeProperty" in block
        or "rdf:type owl:AnnotationProperty" in block
        or "rdf:type rdf:Property" in block
    ):
        return "property"

    if re.search(r'ex:matchedTermType\s+\"[^\"]*#Class\"', block):
        return "class"
    if re.search(r'ex:matchedTermType\s+\"[^\"]*#Property\"', block):
        return "property"

    return "unknown"


class CollaborativeLLMAnnotator:
    def __init__(
        self,
        llm_agents: Sequence,
        candidates: Sequence[OntologyTerm],
        annotation_kind: str,
        *,
        top_k: int = 10,
        min_votes: int = 1,
        score_threshold: float = 0.45,
        expected_agent_count: int = 6,
        system_prompt: Optional[str] = None,
    ):
        if not llm_agents:
            raise ValueError("At least one LLM agent is required.")
        if len(llm_agents) != expected_agent_count:
            raise ValueError(
                f"Exactly {expected_agent_count} LLM agents are required, got {len(llm_agents)}."
            )
        if not candidates:
            raise ValueError("No ontology candidates provided.")

        self.llm_agents = list(llm_agents)
        self.committee = self._build_committee(self.llm_agents)
        self.annotation_kind = annotation_kind
        self.top_k = top_k
        self.min_votes = min_votes
        self.score_threshold = score_threshold
        self.expected_agent_count = expected_agent_count
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Map normalized label to term for efficient validation.
        self._candidate_map: Dict[str, OntologyTerm] = {
            _normalize_label(term.label): term for term in candidates
        }

    def _build_committee(self, llm_agents: Sequence) -> List[InstructionTunedCommitteeMember]:
        members: List[InstructionTunedCommitteeMember] = []
        for index, agent_obj in enumerate(llm_agents):
            if isinstance(agent_obj, InstructionTunedCommitteeMember):
                members.append(agent_obj)
                continue

            profile = DEFAULT_INSTRUCTION_PROFILES[index % len(DEFAULT_INSTRUCTION_PROFILES)]
            members.append(
                InstructionTunedCommitteeMember(
                    name=f"annotator_{index + 1}",
                    agent=agent_obj,
                    instruction=profile,
                )
            )

        return members

    def _default_system_prompt(self) -> str:
        return (
            "You are a strict ontology annotation assistant. "
            "Return valid JSON only, with no markdown."
        )

    def _build_prompt(self, text: str) -> str:
        candidate_list = [
            {
                "label": term.label,
                "iri": term.iri,
                "description": term.description,
            }
            for term in self._candidate_map.values()
        ]

        return (
            f"Task: annotate {self.annotation_kind} from the input text.\n"
            "Use ONLY the provided ontology candidates.\n"
            "Return JSON with this shape:\n"
            '{"annotations": [{"entity": "...", "label": "...", "score": 0.0, "evidence": "..."}]}\n'
            "Entity must be the exact text span from the input text that supports the ontology label.\n"
            "Where score is between 0 and 1.\n"
            f"Input text:\n{text}\n\n"
            f"Ontology candidates:\n{json.dumps(candidate_list, ensure_ascii=False)}"
        )

    def _run_single_agent(self, member: InstructionTunedCommitteeMember, text: str) -> List[Dict]:
        prompt = self._build_prompt(text)
        agent_system_prompt = f"{self.system_prompt}\nRole instruction: {member.instruction}"
        try:
            raw = member.agent.generate_response(prompt, system_prompt=agent_system_prompt)
        except Exception as error:
            error_message = f"{member.name}: {type(error).__name__}: {error}"
            if hasattr(self, "_agent_errors"):
                self._agent_errors.append(error_message)
            print(
                f"[collaborative-annotator] warning: member failed and was skipped -> {error_message}",
                file=sys.stderr,
            )
            return []

        parsed = _extract_json_object(raw)
        annotations = parsed.get("annotations", [])
        if not isinstance(annotations, list):
            return []

        normalized_results: List[Dict] = []
        for item in annotations:
            if not isinstance(item, dict):
                continue

            raw_label = str(item.get("label", "")).strip()
            if not raw_label:
                continue

            canonical = self._candidate_map.get(_normalize_label(raw_label))
            if not canonical:
                continue

            score = _coerce_score(item.get("score", 0.0))
            raw_entity = str(item.get("entity", "")).strip()
            evidence = str(item.get("evidence", "")).strip()
            entity = _resolve_entity_text(raw_entity, evidence, canonical.label, text)
            normalized_results.append(
                {
                    "entity": entity,
                    "label": canonical.label,
                    "iri": canonical.iri,
                    "score": score,
                    "evidence": evidence,
                }
            )

        return normalized_results

    def annotate(self, text: str) -> List[AnnotationCandidate]:
        aggregate: Dict[str, Dict] = {}
        self._agent_errors: List[str] = []

        for member in self.committee:
            annotations = self._run_single_agent(member, text)
            seen_labels = set()
            for ann in annotations:
                label = ann["label"]
                if label in seen_labels:
                    continue
                seen_labels.add(label)

                if label not in aggregate:
                    aggregate[label] = {
                        "annotated_text": text,
                        "entity": ann.get("entity", label),
                        "label": label,
                        "iri": ann["iri"],
                        "total_score": 0.0,
                        "votes": 0,
                        "evidence": [],
                    }

                aggregate[label]["total_score"] += ann["score"]
                aggregate[label]["votes"] += 1
                if ann["evidence"]:
                    aggregate[label]["evidence"].append(ann["evidence"])

        if len(self._agent_errors) == len(self.committee):
            raise RuntimeError(
                "All committee members failed. First errors: "
                + " | ".join(self._agent_errors[:3])
            )

        ranked: List[AnnotationCandidate] = []
        for item in aggregate.values():
            votes = item["votes"]
            avg_score = item["total_score"] / votes if votes else 0.0
            if votes < self.min_votes or avg_score < self.score_threshold:
                continue
            ranked.append(
                AnnotationCandidate(
                    annotated_text=item.get("annotated_text", text),
                    entity=item.get("entity", item["label"]),
                    label=item["label"],
                    iri=item["iri"],
                    score=round(avg_score, 4),
                    votes=votes,
                    evidence=item["evidence"][:3],
                )
            )

        ranked.sort(key=lambda candidate: (-candidate.votes, -candidate.score, candidate.label.lower()))
        return ranked[: self.top_k]


def _normalize_label(label: str) -> str:
    cleaned = (label or "").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _coerce_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _resolve_entity_text(raw_entity: str, evidence: str, fallback_label: str, source_text: str) -> str:
    entity = (raw_entity or "").strip()
    if entity and entity.lower() in (source_text or "").lower():
        return entity

    quoted = re.findall(r'"([^"\n]+)"', evidence or "")
    for value in quoted:
        candidate = value.strip()
        if candidate and candidate.lower() in (source_text or "").lower():
            return candidate

    if evidence and evidence.lower() in (source_text or "").lower():
        return evidence

    return fallback_label
