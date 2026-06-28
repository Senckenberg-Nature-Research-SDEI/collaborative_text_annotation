import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import yaml
from openai import OpenAI

from src.llm.base_llm_agent import BaseLLMAgent


@dataclass
class GPTModelConfig:
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    model_card: Optional[str] = None
    tokenizer_card: Optional[str] = None
    model_kwargs: Dict[str, Any] = field(default_factory=dict)
    api_key: Optional[str] = None


def load_gpt_model_config(config_path: str, model_alias: str = "llm_model") -> GPTModelConfig:
    with open(config_path, "r", encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file)

    models = raw_config.get("models", [])
    selected = None
    for model in models:
        if model.get("name") == model_alias:
            selected = model
            break

    if selected is None:
        raise ValueError(f"Model alias '{model_alias}' not found in {config_path}")

    api_key = selected.get("api_key")
    if isinstance(api_key, str):
        api_key = api_key.strip()
        if api_key.startswith("env:"):
            api_key = os.getenv(api_key.split(":", 1)[1].strip())
        elif api_key.startswith("${") and api_key.endswith("}"):
            api_key = os.getenv(api_key[2:-1].strip())

    return GPTModelConfig(
        model_name=selected["model"],
        temperature=selected.get("temperature", 0.7),
        max_tokens=selected.get("max_tokens", 2048),
        top_p=selected.get("top_p", 0.9),
        model_card=selected.get("model_card"),
        tokenizer_card=selected.get("tokenizer_card"),
        model_kwargs=selected.get("model_kwargs", {}) or {},
        api_key=api_key,
    )


class OpenAIGPTAgent(BaseLLMAgent):
    def __init__(self, config: GPTModelConfig):
        super().__init__(config)
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.client = OpenAI(api_key=api_key)
        self.model_kwargs = config.model_kwargs

    def load_model(self):
        return self.model_name

    def load_tokenizer(self):
        return None

    def _normalize_model_kwargs(self) -> Dict[str, Any]:
        kwargs = dict(self.model_kwargs)
        response_format = kwargs.get("response_format")

        # Accept either "json_object" or the official dict format.
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        return kwargs

    def _create_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        n: int = 1,
    ) -> Union[str, List[str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature if temperature is None else temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p if top_p is None else top_p,
            n=n,
            **self._normalize_model_kwargs(),
        )

        outputs = [choice.message.content or "" for choice in response.choices]
        return outputs[0] if n == 1 else outputs

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return self._create_completion(prompt, system_prompt=system_prompt)

    def beam_search(self, prompt: str, num_beams: int = 5, system_prompt: Optional[str] = None):
        # OpenAI does not expose true beam search; this approximates it via n samples.
        return self._create_completion(
            prompt,
            system_prompt=system_prompt,
            temperature=0.0,
            top_p=1.0,
            n=num_beams,
        )

    def greedy_search(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return self._create_completion(prompt, system_prompt=system_prompt, temperature=0.0, top_p=1.0)

    def nucleus_sampling(self, prompt: str, top_p: float = 0.9, system_prompt: Optional[str] = None) -> str:
        return self._create_completion(
            prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            top_p=top_p,
        )
