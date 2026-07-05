# Collaborative Text Annotation
Information Extraction Tools to annotate type specimen catalogs and competency-question outputs.

## Overview
This repository provides two related workflows:

1. A collaborative six-model annotator for extracting entity and relation annotations from type specimen catalog text.
2. A competency-question pipeline that extracts concepts and properties and serializes them to RDF/Turtle.

The annotation workflow is designed around Hugging Face OpenAI-compatible routing and writes separate outputs for entities and relations.

## Requirements
- Python 3.10+
- `openai`
- `pyyaml`
- A Hugging Face API token in `HF_API_KEY`

Optional environment variables:
- `HF_BASE_URL` - defaults to `https://router.huggingface.co/v1`

## Repository Layout

```
.
├── config/
│   └── model_config.yaml
├── data/
│   ├── competency_questions/
│   │   └── competency_questions.json
│   ├── existing_ontologies/
│   │   ├── dsw-0-3-specimen.ttl
│   │   └── term_versions.csv
│   └── type_specimen_catalogues/
│       ├── out_steffan_catalogues.csv
│       └── out_steffan_catalogues_texts.txt
├── doc/
│   └── user-scenarios/
├── outputs/
│   ├── annotated_entities.jsonl
│   ├── annotated_relations.jsonl
│   ├── annotated_texts.jsonl
│   ├── cq_concepts_properties.jsonl
│   ├── cq_concepts_properties_grouped.json
│   └── cq_concepts_properties.ttl
├── src/
│   ├── llm/
│   ├── collaborative_annotator/
│   ├── schema_generator/
│   └── utils.py
├── run_collaborative_annotation.py
├── run_cq_extraction.sh
├── run_collaborative_annotation.sh
├── run_prompts.py
├── run_turtle_serilizer.sh
└── README.md
```

## Setup
1. Install dependencies.

   ```bash
   pip install openai pyyaml
   ```

2. Export your Hugging Face token.

   ```bash
   export HF_API_KEY="your_hugging_face_token"
   ```

3. Optional: override the Hugging Face OpenAI-compatible endpoint.

   ```bash
   export HF_BASE_URL="https://router.huggingface.co/v1"
   ```

## Collaborative Annotation Workflow
The collaborative annotator uses six instruction-tuned LLM committee members and extracts:
- entities
- relations

The default text source is:
- `data/type_specimen_catalogues/out_steffan_catalogues_texts.txt`

The default outputs are:
- `outputs/annotated_entities.jsonl`
- `outputs/annotated_relations.jsonl`

Evidence is not saved in the final output files.

### Run the annotator
```bash
bash run_collaborative_annotation.sh
```

### Annotate a custom inline text
```bash
bash run_collaborative_annotation.sh --text "Specimen has catalog number ZM-123 and associated media image."
```

### Annotate a different text file
```bash
bash run_collaborative_annotation.sh --text-file path/to/your_texts.txt
```

### Write to custom output paths
```bash
bash run_collaborative_annotation.sh \
  --entity-output outputs/my_entities.jsonl \
  --relation-output outputs/my_relations.jsonl
```

### Optional combined output
If you also want the combined record, pass:

```bash
bash run_collaborative_annotation.sh --output outputs/annotated_texts.jsonl
```

### Output format
Each item in the entity and relation outputs includes:
- `annotated_text`
- `entity`
- `label`
- `iri`
- `score`
- `votes`

## Competency Question Extraction
This workflow extracts concepts and properties from competency questions and writes RDF-ready outputs.

### Run the CQ extraction pipeline
```bash
./run_cq_extraction.sh [input_json] [output_jsonl] [grouped_output_json] [rdf_turtle_output]
```

Defaults:
- input: `data/competency_questions/competency_questions.json`
- jsonl output: `outputs/cq_concepts_properties.jsonl`
- grouped output: `outputs/cq_concepts_properties_grouped.json`
- rdf output: `outputs/cq_concepts_properties.ttl`

### Serialize grouped results to Turtle only
```bash
python src/serialize_cq_results_to_rdf.py \
  --input outputs/cq_concepts_properties_grouped.json \
  --output outputs/cq_concepts_properties.ttl
```

## Prompt Runner
You can also run standalone prompts against the configured model aliases.

### Run prompts
```bash
python run_prompts.py --prompt-file example.txt --model-alias llm_model
```

Useful options:
- `--prompt "your question"` - repeat for multiple prompts
- `--prompt-file path/to/file.txt` - prompts separated by blank lines
- `--output outputs.jsonl` - save results
- `--system-prompt "You are a helpful extraction assistant."`

## Notes
- The collaborative annotator uses a six-model committee.
- Models are configured in `config/model_config.yaml`.
- The Turtle ontology for annotation candidates comes from `outputs/cq_concepts_properties.ttl`.
- The generated text file `data/type_specimen_catalogues/out_steffan_catalogues_texts.txt` is used as the default annotation input.

