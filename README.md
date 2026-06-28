# Memory-based Model Context Protocol
Information Extraction Tools to Annotate Type Specimen Catalogs.

# Memories
* Declarative Memory
* Procedural Memory


## Run Prompts On GPT
1. Install dependencies:
	`pip install openai pyyaml`
2. Export your API key:
	`export OPENAI_API_KEY="your_key_here"`
	(or set `api_key` per model in `config/model_config.yaml`, e.g. `api_key: ${OPENAI_API_KEY}`)
3. Run prompts:
	`python run_prompts.py --prompt-file example.txt --model-alias llm_model`

Useful options:
* `--prompt "your question"` (repeat for multiple prompts)
* `--prompt-file path/to/file.txt` (prompts separated by blank lines)
* `--output outputs.jsonl` (save results)
* `--system-prompt "You are a helpful extraction assistant."`

## Extract Concepts And Properties From Competency Questions
Run:
`./run_cq_extraction.sh [input_json] [output_jsonl] [grouped_output_json] [rdf_turtle_output]`

Defaults:
* input: `data/competency_questions/competency_questions.json`
* jsonl output: `outputs/cq_concepts_properties.jsonl`
* grouped output: `outputs/cq_concepts_properties_grouped.json`
* rdf output: `outputs/cq_concepts_properties.ttl`

Serialize existing grouped results to RDF Turtle only:
`python src/serialize_cq_results_to_rdf.py --input outputs/cq_concepts_properties_grouped.json --output outputs/cq_concepts_properties.ttl`


## MCP with Dynamic Memory Architecture
! wip for figure.

