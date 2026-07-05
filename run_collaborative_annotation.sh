#!/usr/bin/env bash
set -euo pipefail

# Example:
#   ./run_mdp_collaborative_annotation.sh --text "Specimen has catalogNumber ZM-123 and associated media image URL"
#
# Optional environment variables:
#   HF_BASE_URL=https://router.huggingface.co/v1
#   HF_API_KEY=hf_xxx
#   CONFIG_PATH=config/model_config.yaml
#   TTL_PATH=outputs/cq_concepts_properties.ttl
#   ENTITY_OUTPUT_PATH=outputs/annotated_entities.jsonl
#   RELATION_OUTPUT_PATH=outputs/annotated_relations.jsonl

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CONFIG_PATH="${CONFIG_PATH:-config/model_config.yaml}"
TTL_PATH="${TTL_PATH:-outputs/cq_concepts_properties.ttl}"
TEXT_FILE_PATH="${TEXT_FILE_PATH:-data/type_specimen_catalogues/out_steffan_catalogues_texts.txt}"
ENTITY_OUTPUT_PATH="${ENTITY_OUTPUT_PATH:-outputs/annotated_entities.jsonl}"
RELATION_OUTPUT_PATH="${RELATION_OUTPUT_PATH:-outputs/annotated_relations.jsonl}"
export HF_BASE_URL="${HF_BASE_URL:-https://router.huggingface.co/v1}"

if [[ -z "${HF_API_KEY:-}" ]]; then
  echo "HF_API_KEY is not set. Export your Hugging Face token first." >&2
  echo "Example: export HF_API_KEY=hf_xxx" >&2
  exit 1
fi

python run_collaborative_annotation.py \
  --config "$CONFIG_PATH" \
  --ttl "$TTL_PATH" \
  --aliases committee_qwen committee_llama committee_mistral committee_deepseek committee_gemma committee_other \
  $(
    has_text_arg=0
    for arg in "$@"; do
      if [[ "$arg" == "--text" || "$arg" == "--text-file" ]]; then
        has_text_arg=1
        break
      fi
    done
    if [[ "$has_text_arg" -eq 0 ]]; then
      printf -- '--text-file %q ' "$TEXT_FILE_PATH"
    fi
  ) \
  $(
    has_entity_output_arg=0
    for arg in "$@"; do
      if [[ "$arg" == "--entity-output" ]]; then
        has_entity_output_arg=1
        break
      fi
    done
    if [[ "$has_entity_output_arg" -eq 0 ]]; then
      printf -- '--entity-output %q ' "$ENTITY_OUTPUT_PATH"
    fi
  ) \
  $(
    has_relation_output_arg=0
    for arg in "$@"; do
      if [[ "$arg" == "--relation-output" ]]; then
        has_relation_output_arg=1
        break
      fi
    done
    if [[ "$has_relation_output_arg" -eq 0 ]]; then
      printf -- '--relation-output %q ' "$RELATION_OUTPUT_PATH"
    fi
  ) \
  "$@"
