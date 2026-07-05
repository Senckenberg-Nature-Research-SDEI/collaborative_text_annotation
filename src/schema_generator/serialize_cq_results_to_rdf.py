#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def slugify(value: str) -> str:
    text = normalize_apostrophes(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ")
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "item"


def normalize_apostrophes(value: str) -> str:
    return (
        value or ""
    ).replace("’", "'").replace("‘", "'").replace("´", "'")


def ttl_escape(value: str) -> str:
    value = normalize_apostrophes(value)
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def iri_for(base: str, *parts: str) -> str:
    suffix = "/".join(slugify(part) for part in parts)
    return f"{base}{suffix}"


def normalize_key(value: str) -> str:
    return slugify(value)


def add_line(lines, text):
    lines.append(text)


def ensure_entry(registry: dict, key: str, iri: str, label: str) -> dict:
    entry = registry.get(key)
    if entry is None:
        entry = {
            "iri": iri,
            "label": label,
            "descriptions": [],
            "synonyms": [],
            "source_cqs": [],
            "source_labels": [],
            "source_questions": [],
            "matched_term": None,
            "matched_relation": None,
        }
        registry[key] = entry
    return entry


def register_alias(alias_map: dict, alias: str, canonical_key: str) -> None:
    alias_key = normalize_key(alias)
    if alias_key and alias_key not in alias_map:
        alias_map[alias_key] = canonical_key


def add_unique(values: list, value: str) -> None:
    if value and value not in values:
        values.append(value)


def text_tokens(value: str) -> list:
    normalized = normalize_apostrophes(value).lower()
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [token for token in tokens if token not in STOPWORDS]


def combined_text(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def load_term_versions(csv_path: str) -> list[dict]:
    term_rows = []
    with open(csv_path, "r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            term_row = {key: (value or "").strip() for key, value in row.items()}
            term_row["_normalized_label"] = normalize_key(term_row.get("label", ""))
            term_row["_normalized_local_name"] = normalize_key(term_row.get("term_localName", ""))
            term_row["_search_text"] = combined_text(
                term_row.get("label", ""),
                term_row.get("term_localName", ""),
                term_row.get("definition", ""),
                term_row.get("comments", ""),
                term_row.get("examples", ""),
                term_row.get("organized_in", ""),
                term_row.get("term_iri", ""),
            )
            term_rows.append(term_row)
    return term_rows


def build_term_indexes(term_rows: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    recommended_rows = [row for row in term_rows if row.get("status", "").lower() == "recommended" and is_dwc_term(row)]
    exact_label_index = {}
    exact_local_name_index = {}

    for row in recommended_rows:
        normalized_label = row.get("_normalized_label", "")
        normalized_local_name = row.get("_normalized_local_name", "")
        if normalized_label and normalized_label not in exact_label_index:
            exact_label_index[normalized_label] = row
        if normalized_local_name and normalized_local_name not in exact_local_name_index:
            exact_local_name_index[normalized_local_name] = row

    return exact_label_index, exact_local_name_index


def is_dwc_term(row: dict) -> bool:
    term_iri = row.get("term_iri", "")
    return term_iri.startswith("http://rs.tdwg.org/dwc/") or term_iri.startswith("http://rs.tdwg.org/dwc/terms/")


def score_term_match(source_label: str, source_text: str, term_row: dict) -> float:
    source_normalized_label = normalize_key(source_label)
    source_tokens = set(text_tokens(combined_text(source_label, source_text)))
    candidate_tokens = set(text_tokens(term_row.get("_search_text", "")))

    if not source_tokens or not candidate_tokens:
        return 0.0

    overlap = len(source_tokens & candidate_tokens)
    union = len(source_tokens | candidate_tokens)
    score = (overlap / union) * 100.0 if union else 0.0

    term_label = term_row.get("_normalized_label", "")
    term_local_name = term_row.get("_normalized_local_name", "")

    if source_normalized_label and source_normalized_label == term_label:
        score += 70.0
    elif source_normalized_label and source_normalized_label == term_local_name:
        score += 70.0
    elif source_normalized_label and (source_normalized_label in term_label or term_label in source_normalized_label):
        score += 25.0
    elif source_normalized_label and (source_normalized_label in term_local_name or term_local_name in source_normalized_label):
        score += 25.0

    if source_tokens.issubset(candidate_tokens):
        score += 15.0
    if candidate_tokens.issubset(source_tokens):
        score += 5.0

    return score


def match_term(source_label: str, source_text: str, term_rows: list[dict], family: str) -> dict | None:
    if family == "class":
        candidates = [row for row in term_rows if "Class" in row.get("rdf_type", "") and is_dwc_term(row)]
    else:
        candidates = [row for row in term_rows if "Property" in row.get("rdf_type", "") and is_dwc_term(row)]

    exact_label_index, exact_local_name_index = build_term_indexes(term_rows)
    normalized_source_label = normalize_key(source_label)
    exact_match = exact_label_index.get(normalized_source_label) or exact_local_name_index.get(normalized_source_label)
    if exact_match and ((family == "class" and "Class" in exact_match.get("rdf_type", "")) or (family != "class" and "Property" in exact_match.get("rdf_type", ""))):
        result = dict(exact_match)
        result["_score"] = 100.0
        return result

    scored = []
    for row in candidates:
        score = score_term_match(source_label, source_text, row)
        if score > 0:
            scored.append((score, row))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], len(item[1].get("label", "")), item[1].get("label", "")))
    best_score, best_row = scored[0]

    result = dict(best_row)
    result["_score"] = round(best_score, 2)
    return result


def token_sequence(value: str) -> list:
    return [token for token in normalize_key(value).split("-") if token]


def is_parent_label(child_label: str, parent_label: str) -> bool:
    child_tokens = token_sequence(child_label)
    parent_tokens = token_sequence(parent_label)
    if not child_tokens or not parent_tokens:
        return False
    if len(parent_tokens) >= len(child_tokens):
        return False

    child_text = " ".join(child_tokens)
    parent_text = " ".join(parent_tokens)

    if parent_text == child_text:
        return False

    return parent_text in child_text


def infer_super_labels(label: str, candidate_labels: list[str], *, strip_auxiliary_prefixes: bool = False) -> list[str]:
    normalized_label = normalize_key(label)
    candidates = []
    for candidate in candidate_labels:
        normalized_candidate = normalize_key(candidate)
        if normalized_candidate == normalized_label:
            continue
        if is_parent_label(normalized_label, normalized_candidate):
            candidates.append(candidate)

    if strip_auxiliary_prefixes:
        stripped = re.sub(r"^(has|is|are|was|were|related-to|related-to-the|related-to-an|related-to-a)-", "", normalized_label)
        for candidate in candidate_labels:
            normalized_candidate = normalize_key(candidate)
            if normalized_candidate == normalized_label:
                continue
            if normalized_candidate == stripped or is_parent_label(stripped, normalized_candidate):
                candidates.append(candidate)

    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    unique_candidates.sort(key=lambda value: (-len(token_sequence(value)), len(value), value))
    return unique_candidates

def concept_type_iri(concept: dict) -> str | None:
    matched_term = concept.get("matched_term")
    if matched_term:
        return matched_term.get("term_iri") or None
    return concept.get("iri")

def concept_ref_for_label(label: str, concept_registry: dict, concept_aliases: dict) -> str | None:
    concept_key = concept_aliases.get(normalize_key(label))
    if not concept_key:
        return None

    concept_entry = concept_registry.get(concept_key)
    if not concept_entry:
        return None

    return concept_type_iri(concept_entry) or concept_entry.get("iri")


def property_ref_for_label(label: str, property_registry: dict, property_aliases: dict) -> str | None:
    property_key = property_aliases.get(normalize_key(label))
    if not property_key:
        return None

    property_entry = property_registry.get(property_key)
    if not property_entry:
        return None

    matched_term = property_entry.get("matched_term")
    if matched_term:
        return matched_term.get("term_iri") or None

    return None


def build_ttl(data: dict, base_iri: str, term_rows: list[dict]) -> str:
    lines = []
    add_line(lines, "@prefix ex: <https://example.org/cq/> .")
    add_line(lines, "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    add_line(lines, "@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    add_line(lines, "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    add_line(lines, "@prefix dcterms: <http://purl.org/dc/terms/> .")
    add_line(lines, "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
    add_line(lines, "")

    story_map = data.get("by_user_story", {})
    concept_registry = {}
    concept_aliases = {}
    property_registry = {}
    property_aliases = {}
    individual_registry = {}

    for story_name, cqs in story_map.items():
        story_iri = iri_for(base_iri, "story", story_name)
        add_line(lines, f"<{story_iri}> a ex:UserStory ;")
        add_line(lines, f"  rdfs:label \"{ttl_escape(story_name)}\" .")
        add_line(lines, "")

        for cq_id, payload in (cqs or {}).items():
            cq_title = payload.get("cq_title", "")
            question = payload.get("question", "")
            cq_iri = iri_for(base_iri, "cq", story_name, cq_id)

            add_line(lines, f"<{cq_iri}> a ex:CompetencyQuestion ;")
            add_line(lines, f"  dcterms:identifier \"{ttl_escape(cq_id)}\" ;")
            add_line(lines, f"  rdfs:label \"{ttl_escape(cq_title)}\" ;")
            add_line(lines, f"  ex:questionText \"{ttl_escape(question)}\" ;")
            add_line(lines, f"  ex:inUserStory <{story_iri}> .")
            add_line(lines, "")

            for concept in payload.get("concepts", []):
                label = concept.get("label", "")
                canonical_key = concept_aliases.get(normalize_key(label), normalize_key(label))
                concept_iri = iri_for(base_iri, "concept", canonical_key)
                concept_entry = ensure_entry(concept_registry, canonical_key, concept_iri, label)

                add_unique(concept_entry["source_cqs"], cq_iri)
                add_unique(concept_entry["source_labels"], label)
                add_unique(concept_entry["source_questions"], question)

                description = concept.get("description")
                if description:
                    add_unique(concept_entry["descriptions"], description)

                register_alias(concept_aliases, label, canonical_key)
                for synonym in concept.get("synonyms", []):
                    add_unique(concept_entry["synonyms"], synonym)
                    register_alias(concept_aliases, synonym, canonical_key)

            for prop in payload.get("properties", []):
                label = prop.get("label", "")
                canonical_key = property_aliases.get(normalize_key(label), normalize_key(label))
                prop_iri = iri_for(base_iri, "property", canonical_key)
                property_entry = ensure_entry(property_registry, canonical_key, prop_iri, label)

                add_unique(property_entry["source_cqs"], cq_iri)
                add_unique(property_entry["source_labels"], label)
                add_unique(property_entry["source_questions"], question)

                description = prop.get("description")
                if description:
                    add_unique(property_entry["descriptions"], description)

                register_alias(property_aliases, label, canonical_key)

                domain = (prop.get("domain") or "").strip()
                range_ = (prop.get("range") or "").strip()
                if domain:
                    property_entry.setdefault("domains", [])
                    add_unique(property_entry["domains"], domain)
                if range_:
                    property_entry.setdefault("ranges", [])
                    add_unique(property_entry["ranges"], range_)

    concept_labels = [entry["label"] for entry in concept_registry.values()]
    property_labels = [entry["label"] for entry in property_registry.values()]

    for concept in concept_registry.values():
        source_text = combined_text(
            " ".join(concept.get("descriptions", [])),
            " ".join(concept.get("synonyms", [])),
            " ".join(concept.get("source_questions", [])),
        )
        matched_term = match_term(concept["label"], source_text, term_rows, "class")
        if matched_term:
            concept["matched_term"] = matched_term
            concept["matched_relation"] = (
                "exactMatch"
                if normalize_key(concept["label"]) in {matched_term.get("_normalized_label", ""), matched_term.get("_normalized_local_name", "")}
                else "closeMatch"
            )
        else:
            parents = infer_super_labels(concept["label"], concept_labels)
            if parents:
                concept["parents"] = parents[:3]

        individual_key = normalize_key(concept["label"])
        individual_iri = iri_for(base_iri, "individual", individual_key)
        individual_entry = ensure_entry(individual_registry, individual_key, individual_iri, concept["label"])
        for source_cq in concept.get("source_cqs", []):
            add_unique(individual_entry["source_cqs"], source_cq)
        add_unique(individual_entry["source_labels"], concept["label"])
        for source_question in concept.get("source_questions", []):
            add_unique(individual_entry["source_questions"], source_question)
        for description in concept.get("descriptions", []):
            add_unique(individual_entry["descriptions"], description)
        for synonym in concept.get("synonyms", []):
            add_unique(individual_entry["synonyms"], synonym)
        if concept.get("matched_term"):
            individual_entry["matched_term"] = concept["matched_term"]
            individual_entry["matched_relation"] = concept.get("matched_relation")

    for prop in property_registry.values():
        source_text = combined_text(
            " ".join(prop.get("descriptions", [])),
            " ".join(prop.get("source_questions", [])),
            " ".join(prop.get("source_labels", [])),
        )
        matched_term = match_term(prop["label"], source_text, term_rows, "property")
        if matched_term:
            prop["matched_term"] = matched_term
            prop["matched_relation"] = (
                "exactMatch"
                if normalize_key(prop["label"]) in {matched_term.get("_normalized_label", ""), matched_term.get("_normalized_local_name", "")}
                else "closeMatch"
            )
        else:
            parents = infer_super_labels(prop["label"], property_labels, strip_auxiliary_prefixes=True)
            if parents:
                prop["parents"] = parents[:3]

    for key, concept in concept_registry.items():
        add_line(lines, f"<{concept['iri']}> a owl:Class, ex:Concept ;")
        add_line(lines, f"  rdfs:label \"{ttl_escape(concept['label'])}\" ;")

        matched_term = concept.get("matched_term")
        if matched_term:
            add_line(lines, f"  owl:equivalentClass <{matched_term['term_iri']}> ;")
            add_line(lines, f"  skos:{concept.get('matched_relation', 'closeMatch')} <{matched_term['term_iri']}> ;")
            add_line(lines, f"  ex:matchedTermIRI \"{ttl_escape(matched_term.get('term_iri', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermLabel \"{ttl_escape(matched_term.get('label', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermLocalName \"{ttl_escape(matched_term.get('term_localName', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermType \"{ttl_escape(matched_term.get('rdf_type', ''))}\" ;")
            add_line(lines, f"  ex:termMatchScore \"{ttl_escape(str(matched_term.get('_score', '')))}\" ;")

        for parent_label in concept.get("parents", []):
            parent_key = normalize_key(parent_label)
            parent_entry = concept_registry.get(parent_key)
            if parent_entry:
                add_line(lines, f"  rdfs:subClassOf <{parent_entry['iri']}> ;")

        for description in concept.get("descriptions", []):
            add_line(lines, f"  dcterms:description \"{ttl_escape(description)}\" ;")
            add_line(lines, f"  skos:definition \"{ttl_escape(description)}\" ;")
            add_line(lines, f"  rdfs:comment \"{ttl_escape(description)}\" ;")

        for synonym in concept.get("synonyms", []):
            add_line(lines, f"  skos:altLabel \"{ttl_escape(synonym)}\" ;")

        for source_cq in concept.get("source_cqs", []):
            add_line(lines, f"  ex:extractedFrom <{source_cq}> ;")

        for source_cq in concept.get("source_cqs", []):
            add_line(lines, f"  dcterms:source <{source_cq}> ;")

        for source_label in concept.get("source_labels", []):
            add_line(lines, f"  ex:sourceLabel \"{ttl_escape(source_label)}\" ;")

        for source_question in concept.get("source_questions", []):
            add_line(lines, f"  ex:sourceQuestion \"{ttl_escape(source_question)}\" ;")

        add_line(lines, f"  rdfs:isDefinedBy <https://example.org/cq/> ;")

        lines[-1] = lines[-1].rstrip(" ;") + " ."
        add_line(lines, "")

    for key, individual in individual_registry.items():
        concept_entry = concept_registry.get(key)
        individual_type = concept_type_iri(concept_entry) if concept_entry else None

        add_line(lines, f"<{individual['iri']}> a ex:ExtractedIndividual")
        if individual_type:
            add_line(lines, f", <{individual_type}> ;")
        else:
            add_line(lines, " ;")

        add_line(lines, f"  rdfs:label \"{ttl_escape(individual['label'])}\" ;")

        if concept_entry:
            add_line(lines, f"  ex:derivedFromConcept <{concept_entry['iri']}> ;")

        matched_term = individual.get("matched_term")
        if matched_term:
            add_line(lines, f"  ex:matchedTermIRI \"{ttl_escape(matched_term.get('term_iri', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermLabel \"{ttl_escape(matched_term.get('label', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermLocalName \"{ttl_escape(matched_term.get('term_localName', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermType \"{ttl_escape(matched_term.get('rdf_type', ''))}\" ;")
            add_line(lines, f"  ex:termMatchScore \"{ttl_escape(str(matched_term.get('_score', '')))}\" ;")

        for description in individual.get("descriptions", []):
            add_line(lines, f"  dcterms:description \"{ttl_escape(description)}\" ;")
            add_line(lines, f"  skos:definition \"{ttl_escape(description)}\" ;")
            add_line(lines, f"  rdfs:comment \"{ttl_escape(description)}\" ;")

        for synonym in individual.get("synonyms", []):
            add_line(lines, f"  skos:altLabel \"{ttl_escape(synonym)}\" ;")

        for source_cq in individual.get("source_cqs", []):
            add_line(lines, f"  dcterms:source <{source_cq}> ;")

        for source_label in individual.get("source_labels", []):
            add_line(lines, f"  ex:sourceLabel \"{ttl_escape(source_label)}\" ;")

        for source_question in individual.get("source_questions", []):
            add_line(lines, f"  ex:sourceQuestion \"{ttl_escape(source_question)}\" ;")

        add_line(lines, f"  rdfs:isDefinedBy <https://example.org/cq/> ;")

        lines[-1] = lines[-1].rstrip(" ;") + " ."
        add_line(lines, "")

    for key, prop in property_registry.items():
        matched_term = prop.get("matched_term")
        subject_iri = matched_term.get("term_iri") if matched_term else prop["iri"]

        if matched_term:
            add_line(lines, f"<{subject_iri}> a rdf:Property ;")
            add_line(lines, f"  rdfs:label \"{ttl_escape(matched_term.get('label', prop['label']))}\" ;")
        else:
            add_line(lines, f"<{subject_iri}> a rdf:Property, ex:ExtractedProperty ;")
            add_line(lines, f"  rdfs:label \"{ttl_escape(prop['label'])}\" ;")

        if matched_term:
            add_line(lines, f"  ex:matchedTermIRI \"{ttl_escape(matched_term.get('term_iri', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermLabel \"{ttl_escape(matched_term.get('label', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermLocalName \"{ttl_escape(matched_term.get('term_localName', ''))}\" ;")
            add_line(lines, f"  ex:matchedTermType \"{ttl_escape(matched_term.get('rdf_type', ''))}\" ;")
            add_line(lines, f"  ex:termMatchScore \"{ttl_escape(str(matched_term.get('_score', '')))}\" ;")
            add_line(lines, f"  ex:dwcPropertyIRI \"{ttl_escape(matched_term.get('term_iri', ''))}\" ;")
            add_line(lines, f"  ex:dwcPropertyLabel \"{ttl_escape(matched_term.get('label', ''))}\" ;")
            add_line(lines, f"  ex:dwcPropertyLocalName \"{ttl_escape(matched_term.get('term_localName', ''))}\" ;")
            add_line(lines, f"  ex:dwcPropertyType \"{ttl_escape(matched_term.get('rdf_type', ''))}\" ;")

        for domain in prop.get("domains", []):
            domain_ref = concept_ref_for_label(domain, concept_registry, concept_aliases)
            if domain_ref:
                add_line(lines, f"  rdfs:domain <{domain_ref}> ;")
            else:
                add_line(lines, f"  ex:domainText \"{ttl_escape(domain)}\" ;")

        for range_ in prop.get("ranges", []):
            range_ref = concept_ref_for_label(range_, concept_registry, concept_aliases)
            if range_ref:
                add_line(lines, f"  rdfs:range <{range_ref}> ;")
            else:
                add_line(lines, f"  ex:rangeText \"{ttl_escape(range_)}\" ;")

        dwc_property_ref = property_ref_for_label(prop.get("label", ""), property_registry, property_aliases)
        if not matched_term and dwc_property_ref:
            add_line(lines, f"  ex:mapsToDwcProperty <{dwc_property_ref}> ;")

        for parent_label in prop.get("parents", []):
            parent_key = normalize_key(parent_label)
            parent_entry = property_registry.get(parent_key)
            if parent_entry:
                add_line(lines, f"  rdfs:subPropertyOf <{parent_entry['iri']}> ;")

        for description in prop.get("descriptions", []):
            add_line(lines, f"  dcterms:description \"{ttl_escape(description)}\" ;")
            add_line(lines, f"  skos:definition \"{ttl_escape(description)}\" ;")
            add_line(lines, f"  rdfs:comment \"{ttl_escape(description)}\" ;")

        for source_cq in prop.get("source_cqs", []):
            add_line(lines, f"  ex:extractedFrom <{source_cq}> ;")

        for source_cq in prop.get("source_cqs", []):
            add_line(lines, f"  dcterms:source <{source_cq}> ;")

        for source_label in prop.get("source_labels", []):
            add_line(lines, f"  ex:sourceLabel \"{ttl_escape(source_label)}\" ;")

        for source_question in prop.get("source_questions", []):
            add_line(lines, f"  ex:sourceQuestion \"{ttl_escape(source_question)}\" ;")

        add_line(lines, f"  rdfs:isDefinedBy <https://example.org/cq/> ;")

        lines[-1] = lines[-1].rstrip(" ;") + " ."
        add_line(lines, "")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Serialize grouped CQ extraction results to RDF Turtle")
    parser.add_argument("--input", default="outputs/cq_concepts_properties_grouped.json", help="Input grouped JSON path")
    parser.add_argument("--output", default="outputs/type_specimen_schema.ttl", help="Output Turtle path")
    parser.add_argument("--term-versions", default="data/existing_ontologies/term_versions.csv", help="Term versions CSV path")
    parser.add_argument("--base-iri", default="https://example.org/cq/", help="Base IRI for minted resources")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    term_rows = load_term_versions(args.term_versions)
    ttl = build_ttl(data, args.base_iri, term_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ttl, encoding="utf-8")
    print(f"RDF Turtle written to: {output_path}")


if __name__ == "__main__":
    main()
