#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "item"


def ttl_escape(value: str) -> str:
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def iri_for(base: str, *parts: str) -> str:
    suffix = "/".join(slugify(part) for part in parts)
    return f"{base}{suffix}"


def add_line(lines, text):
    lines.append(text)


def build_ttl(data: dict, base_iri: str) -> str:
    lines = []
    add_line(lines, "@prefix ex: <https://example.org/cq/> .")
    add_line(lines, "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    add_line(lines, "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    add_line(lines, "@prefix dcterms: <http://purl.org/dc/terms/> .")
    add_line(lines, "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
    add_line(lines, "")

    story_map = data.get("by_user_story", {})
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

            concept_iris = {}
            for concept in payload.get("concepts", []):
                label = concept.get("label", "")
                concept_iri = iri_for(base_iri, "concept", story_name, cq_id, label)
                concept_iris[label.strip().lower()] = concept_iri

                add_line(lines, f"<{concept_iri}> a ex:Concept ;")
                add_line(lines, f"  rdfs:label \"{ttl_escape(label)}\" ;")

                description = concept.get("description")
                if description:
                    add_line(lines, f"  dcterms:description \"{ttl_escape(description)}\" ;")

                for synonym in concept.get("synonyms", []):
                    add_line(lines, f"  skos:altLabel \"{ttl_escape(synonym)}\" ;")

                add_line(lines, f"  ex:extractedFrom <{cq_iri}> .")
                add_line(lines, "")

            for prop in payload.get("properties", []):
                label = prop.get("label", "")
                prop_iri = iri_for(base_iri, "property", story_name, cq_id, label)
                domain = (prop.get("domain") or "").strip()
                range_ = (prop.get("range") or "").strip()
                description = prop.get("description")

                add_line(lines, f"<{prop_iri}> a rdf:Property, ex:ExtractedProperty ;")
                add_line(lines, f"  rdfs:label \"{ttl_escape(label)}\" ;")

                if description:
                    add_line(lines, f"  dcterms:description \"{ttl_escape(description)}\" ;")

                domain_ref = concept_iris.get(domain.lower()) if domain else None
                range_ref = concept_iris.get(range_.lower()) if range_ else None

                if domain_ref:
                    add_line(lines, f"  rdfs:domain <{domain_ref}> ;")
                elif domain:
                    add_line(lines, f"  ex:domainText \"{ttl_escape(domain)}\" ;")

                if range_ref:
                    add_line(lines, f"  rdfs:range <{range_ref}> ;")
                elif range_:
                    add_line(lines, f"  ex:rangeText \"{ttl_escape(range_)}\" ;")

                add_line(lines, f"  ex:extractedFrom <{cq_iri}> .")
                add_line(lines, "")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Serialize grouped CQ extraction results to RDF Turtle")
    parser.add_argument("--input", default="outputs/cq_concepts_properties_grouped.json", help="Input grouped JSON path")
    parser.add_argument("--output", default="outputs/cq_concepts_properties.ttl", help="Output Turtle path")
    parser.add_argument("--base-iri", default="https://example.org/cq/", help="Base IRI for minted resources")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    ttl = build_ttl(data, args.base_iri)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ttl, encoding="utf-8")
    print(f"RDF Turtle written to: {output_path}")


if __name__ == "__main__":
    main()
