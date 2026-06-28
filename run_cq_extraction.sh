#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-data/competency_questions/competency_questions.json}"
OUTPUT_FILE="${2:-outputs/cq_concepts_properties.jsonl}"
GROUPED_OUTPUT_FILE="${3:-outputs/cq_concepts_properties_grouped.json}"
MODEL_ALIAS="${MODEL_ALIAS:-llm_model}"
CONFIG_FILE="${CONFIG_FILE:-config/model_config.yaml}"

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Input file not found: $INPUT_FILE"
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"
mkdir -p "$(dirname "$GROUPED_OUTPUT_FILE")"
TMP_PROMPTS_FILE="$(mktemp)"
SYSTEM_PROMPT_FILE="$(mktemp)"

cleanup() {
  rm -f "$TMP_PROMPTS_FILE" "$SYSTEM_PROMPT_FILE"
}
trap cleanup EXIT

cat > "$SYSTEM_PROMPT_FILE" <<'EOF'
You are an ontology engineering assistant.
Extract candidate ontology concepts and properties from each competency question.
Return one strict JSON object with this shape:
{
  "user_story": "string",
  "cq_id": "string",
  "cq_title": "string",
  "question": "string",
  "concepts": [
    {
      "label": "string",
      "description": "short definition",
      "synonyms": ["string"]
    }
  ],
  "properties": [
    {
      "label": "string",
      "domain": "string",
      "range": "string",
      "description": "short definition"
    }
  ]
}
Rules:
- Keep labels concise and singular.
- Use only information implied by the question.
- If uncertain, leave a shorter list instead of inventing details.
EOF

python - <<'PY' "$INPUT_FILE" "$TMP_PROMPTS_FILE"
import json
import sys

input_path, output_path = sys.argv[1], sys.argv[2]

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

prompts = []
for item in data:
    story = item.get("user_story", {})
    story_title = story.get("title", "")
    for cq in story.get("competency_questions", []):
        cq_id = cq.get("id", "")
        cq_title = cq.get("title", "")
        question = cq.get("question", "")
        prompt = (
            f"User Story: {story_title}\n"
            f"CQ ID: {cq_id}\n"
            f"CQ Title: {cq_title}\n"
            f"Question: {question}\n"
            "Task: Extract candidate ontology concepts and properties."
        )
        prompts.append(prompt)

with open(output_path, "w", encoding="utf-8") as out:
    out.write("\n\n".join(prompts))
PY

python run_prompts.py \
  --config "$CONFIG_FILE" \
  --model-alias "$MODEL_ALIAS" \
  --system-prompt "$(cat "$SYSTEM_PROMPT_FILE")" \
  --prompt-file "$TMP_PROMPTS_FILE" \
  --output "$OUTPUT_FILE"

python - <<'PY' "$OUTPUT_FILE" "$GROUPED_OUTPUT_FILE"
import json
import re
import sys
from collections import OrderedDict

jsonl_path, grouped_path = sys.argv[1], sys.argv[2]


def parse_response_payload(text):
  text = (text or "").strip()
  if not text:
    return None

  if text.startswith("```"):
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)

  try:
    return json.loads(text)
  except json.JSONDecodeError:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
      candidate = text[start : end + 1]
      try:
        return json.loads(candidate)
      except json.JSONDecodeError:
        return None
    return None


grouped = OrderedDict()
invalid_rows = []

with open(jsonl_path, "r", encoding="utf-8") as f:
  for line_no, line in enumerate(f, start=1):
    line = line.strip()
    if not line:
      continue

    row = json.loads(line)
    payload = parse_response_payload(row.get("response", ""))
    if payload is None:
      invalid_rows.append(line_no)
      continue

    user_story = payload.get("user_story", "UNKNOWN")
    cq_id = payload.get("cq_id", "UNKNOWN")

    if user_story not in grouped:
      grouped[user_story] = OrderedDict()

    grouped[user_story][cq_id] = payload

result = {
  "summary": {
    "stories": len(grouped),
    "entries": sum(len(cqs) for cqs in grouped.values()),
    "invalid_rows": invalid_rows,
  },
  "by_user_story": grouped,
}

with open(grouped_path, "w", encoding="utf-8") as out:
  json.dump(result, out, ensure_ascii=False, indent=2)
PY

echo "Extraction complete. Results saved to: $OUTPUT_FILE"
echo "Grouped output saved to: $GROUPED_OUTPUT_FILE"
