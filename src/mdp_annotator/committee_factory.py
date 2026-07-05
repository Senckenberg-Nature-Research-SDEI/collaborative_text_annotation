from dataclasses import replace
from typing import List, Optional, Sequence

from src.llm.openai_gpt_agent import OpenAIGPTAgent, load_gpt_model_config
from src.mdp_annotator.collaborative_annotator import (
    DEFAULT_INSTRUCTION_PROFILES,
    InstructionTunedCommitteeMember,
)


def build_instruction_tuned_committee(
    config_path: str = "config/model_config.yaml",
    *,
    model_aliases: Optional[Sequence[str]] = None,
) -> List[InstructionTunedCommitteeMember]:
    """Build exactly six instruction-tuned LLM committee members.

    If aliases are not provided, the same alias is reused six times.
    """
    aliases = list(model_aliases) if model_aliases is not None else ["llm_model"] * 6
    if len(aliases) != 6:
        raise ValueError(f"Exactly 6 model aliases are required, got {len(aliases)}.")

    # Slight temperature spread creates complementary behavior across the committee.
    temperatures = [0.2, 0.35, 0.5, 0.65, 0.8, 0.95]

    members: List[InstructionTunedCommitteeMember] = []
    for index, (alias, role_instruction, temp) in enumerate(
        zip(aliases, DEFAULT_INSTRUCTION_PROFILES, temperatures),
        start=1,
    ):
        config = load_gpt_model_config(config_path, alias)
        tuned_config = replace(config, temperature=temp)
        agent = OpenAIGPTAgent(tuned_config)
        members.append(
            InstructionTunedCommitteeMember(
                name=f"instruction_tuned_{index}",
                agent=agent,
                instruction=role_instruction,
            )
        )

    return members
