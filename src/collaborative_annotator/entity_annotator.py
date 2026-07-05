from pathlib import Path
from typing import Optional, Sequence

from src.collaborative_annotator.committee_factory import build_instruction_tuned_committee
from src.collaborative_annotator.collaborative_annotator import CollaborativeLLMAnnotator, TTLConceptCatalog


class CollaborativeEntityAnnotator(CollaborativeLLMAnnotator):
	DEFAULT_SYSTEM_PROMPT_PATH = "data/prompts/entity_system_prompt.txt"

	@staticmethod
	def _entity_system_prompt() -> str:
		return (
			"You are a strict entity annotation assistant for biodiversity specimen text. "
			"Your task is to map text mentions to ontology class labels only from the provided candidates. "
			"For each annotation, return entity as an exact span from the input text and label as the ontology class label. "
			"Do not invent entities, do not output labels not present in candidates, and do not return markdown. "
			"If uncertain, omit the annotation."
		)

	@classmethod
	def _load_system_prompt(cls, prompt_path: Optional[str]) -> str:
		if prompt_path:
			path = Path(prompt_path)
			if path.exists():
				loaded = path.read_text(encoding="utf-8").strip()
				if loaded:
					return loaded
		return cls._entity_system_prompt()

	@classmethod
	def from_instruction_tuned_committee(
		cls,
		config_path: str = "config/model_config.yaml",
		*,
		model_aliases: Optional[Sequence[str]] = None,
		ttl_path: str = "outputs/type_specimen_schema.ttl",
		system_prompt_path: Optional[str] = DEFAULT_SYSTEM_PROMPT_PATH,
		top_k: int = 10,
		min_votes: int = 1,
		score_threshold: float = 0.45,
	):
		members = build_instruction_tuned_committee(
			config_path,
			model_aliases=model_aliases,
		)
		return cls(
			llm_agents=members,
			ttl_path=ttl_path,
			system_prompt_path=system_prompt_path,
			top_k=top_k,
			min_votes=min_votes,
			score_threshold=score_threshold,
		)

	def __init__(
		self,
		llm_agents: Sequence,
		ttl_path: str = "outputs/type_specimen_schema.ttl",
		*,
		system_prompt_path: Optional[str] = DEFAULT_SYSTEM_PROMPT_PATH,
		expected_agent_count: int = 6,
		top_k: int = 10,
		min_votes: int = 1,
		score_threshold: float = 0.45,
	):
		catalog = TTLConceptCatalog.from_ttl_file(ttl_path)
		system_prompt = self._load_system_prompt(system_prompt_path)
		super().__init__(
			llm_agents=llm_agents,
			candidates=catalog.class_terms,
			annotation_kind="entity classes",
			expected_agent_count=expected_agent_count,
			top_k=top_k,
			min_votes=min_votes,
			score_threshold=score_threshold,
			system_prompt=system_prompt,
		)
