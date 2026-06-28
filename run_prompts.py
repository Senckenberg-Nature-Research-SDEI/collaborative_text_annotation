#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import List

from src.llm.openai_gpt_agent import OpenAIGPTAgent, load_gpt_model_config


def read_prompts_from_file(path: Path) -> List[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    # Split by blank lines so multi-line prompts are preserved.
    chunks = [chunk.strip() for chunk in content.split("\n\n")]
    return [chunk for chunk in chunks if chunk]


def collect_prompts(inline_prompts: List[str], prompt_files: List[str]) -> List[str]:
    prompts = list(inline_prompts)
    for file_path in prompt_files:
        prompts.extend(read_prompts_from_file(Path(file_path)))
    return prompts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run prompts on GPT using config/model_config.yaml")
    parser.add_argument("--prompt", action="append", default=[], help="Prompt text. Repeat for multiple prompts.")
    parser.add_argument(
        "--prompt-file",
        action="append",
        default=[],
        help="Path to text file containing prompts separated by blank lines.",
    )
    parser.add_argument("--config", default="config/model_config.yaml", help="Path to model config YAML.")
    parser.add_argument("--model-alias", default="llm_model", help="Model alias from config file.")
    parser.add_argument("--system-prompt", default=None, help="Optional system message.")
    parser.add_argument("--output", default=None, help="Optional output JSONL file.")
    args = parser.parse_args()

    prompts = collect_prompts(args.prompt, args.prompt_file)
    if not prompts:
        raise SystemExit("No prompts found. Use --prompt or --prompt-file.")

    config = load_gpt_model_config(args.config, args.model_alias)
    agent = OpenAIGPTAgent(config)

    output_path = Path(args.output) if args.output else None
    output_handle = output_path.open("w", encoding="utf-8") if output_path else None

    try:
        for index, prompt in enumerate(prompts, start=1):
            response = agent.generate_response(prompt, system_prompt=args.system_prompt)

            print(f"\n=== Prompt {index} ===")
            print(prompt)
            print(f"\n=== Response {index} ===")
            print(response)

            if output_handle:
                record = {"index": index, "prompt": prompt, "response": response}
                output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    finally:
        if output_handle:
            output_handle.close()


if __name__ == "__main__":
    main()
