#!/usr/bin/env python3
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from src.collaborative_annotator.committee_factory import build_instruction_tuned_committee
from src.collaborative_annotator.entity_annotator import CollaborativeEntityAnnotator
from src.collaborative_annotator.relation_annotator import CollaborativeRelationAnnotator


def _read_texts(text_args: List[str], text_file: Optional[str]) -> List[str]:
    texts: List[str] = []
    texts.extend([t.strip() for t in (text_args or []) if t and t.strip()])

    if text_file:
        content = Path(text_file).read_text(encoding="utf-8")
        for line in content.splitlines():
            cleaned = line.strip()
            if cleaned:
                texts.append(cleaned)

    return texts


def _without_evidence(items: List[dict], source_text: str) -> List[dict]:
    cleaned: List[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record = {k: v for k, v in item.items() if k != "evidence"}
        if not record.get("annotated_text"):
            record["annotated_text"] = source_text
        if not record.get("entity"):
            record["entity"] = record.get("label", "")
        cleaned.append(record)
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 6-model collaborative MDP annotation")
    parser.add_argument("--text", action="append", default=[], help="Input text to annotate. Repeatable.")
    parser.add_argument("--text-file", default=None, help="Optional path to a file with one text per line.")
    parser.add_argument("--config", default="config/model_config.yaml", help="Model config path.")
    parser.add_argument(
        "--ttl",
        default="outputs/cq_concepts_properties.ttl",
        help="Ontology TTL path for classes/properties.",
    )
    parser.add_argument(
        "--aliases",
        nargs=6,
        default=[
            "committee_qwen",
            "committee_llama",
            "committee_mistral",
            "committee_deepseek",
            "committee_gemma",
            "committee_other",
        ],
        help="Exactly 6 model aliases in committee order.",
    )
    parser.add_argument("--output", default=None, help="Optional output JSONL path.")
    parser.add_argument("--entity-output", default=None, help="Optional entity annotations JSONL path.")
    parser.add_argument("--relation-output", default=None, help="Optional relation annotations JSONL path.")
    args = parser.parse_args()

    texts = _read_texts(args.text, args.text_file)
    if not texts:
        raise SystemExit("No input texts provided. Use --text or --text-file.")

    committee = build_instruction_tuned_committee(
        config_path=args.config,
        model_aliases=args.aliases,
    )

    entity_annotator = CollaborativeEntityAnnotator(
        llm_agents=committee,
        ttl_path=args.ttl,
    )
    relation_annotator = CollaborativeRelationAnnotator(
        llm_agents=committee,
        ttl_path=args.ttl,
    )

    output_handle = Path(args.output).open("w", encoding="utf-8") if args.output else None
    entity_output_handle = Path(args.entity_output).open("w", encoding="utf-8") if args.entity_output else None
    relation_output_handle = Path(args.relation_output).open("w", encoding="utf-8") if args.relation_output else None
    try:
        for index, text in enumerate(texts, start=1):
            entities = _without_evidence([asdict(item) for item in entity_annotator.annotate(text)], text)
            relations = _without_evidence([asdict(item) for item in relation_annotator.annotate(text)], text)

            entity_payload = {
                "index": index,
                "text": text,
                "entities": entities,
            }
            relation_payload = {
                "index": index,
                "text": text,
                "relations": relations,
            }
            payload = {
                "index": index,
                "text": text,
                "entities": entities,
                "relations": relations,
            }

            print(json.dumps(payload, ensure_ascii=False, indent=2))
            if output_handle:
                output_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            if entity_output_handle:
                entity_output_handle.write(json.dumps(entity_payload, ensure_ascii=False) + "\n")
            if relation_output_handle:
                relation_output_handle.write(json.dumps(relation_payload, ensure_ascii=False) + "\n")
    finally:
        if output_handle:
            output_handle.close()
        if entity_output_handle:
            entity_output_handle.close()
        if relation_output_handle:
            relation_output_handle.close()


if __name__ == "__main__":
    main()
