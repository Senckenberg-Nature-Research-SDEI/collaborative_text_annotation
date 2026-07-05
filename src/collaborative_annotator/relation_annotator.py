from typing import Optional, Sequence

from src.mdp_annotator.committee_factory import build_instruction_tuned_committee
from src.mdp_annotator.collaborative_annotator import CollaborativeLLMAnnotator, TTLConceptCatalog


class CollaborativeRelationAnnotator(CollaborativeLLMAnnotator):
	@classmethod
	def from_instruction_tuned_committee(
		cls,
		config_path: str = "config/model_config.yaml",
		*,
		model_aliases: Optional[Sequence[str]] = None,
		ttl_path: str = "outputs/cq_concepts_properties.ttl",
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
			top_k=top_k,
			min_votes=min_votes,
			score_threshold=score_threshold,
		)

	def __init__(
		self,
		llm_agents: Sequence,
		ttl_path: str = "outputs/cq_concepts_properties.ttl",
		*,
		expected_agent_count: int = 6,
		top_k: int = 10,
		min_votes: int = 1,
		score_threshold: float = 0.45,
	):
		catalog = TTLConceptCatalog.from_ttl_file(ttl_path)
		super().__init__(
			llm_agents=llm_agents,
			candidates=catalog.property_terms,
			annotation_kind="relations/properties",
			expected_agent_count=expected_agent_count,
			top_k=top_k,
			min_votes=min_votes,
			score_threshold=score_threshold,
		)
