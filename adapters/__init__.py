"""Adapter wrappers for project capability domains."""

from adapters.base.wrapper import BasePolicyAdapter
from adapters.motion.wrapper import MotionAssetAdapter
from adapters.skill.wrapper import SkillPolicyAdapter

__all__ = ["MotionAssetAdapter", "BasePolicyAdapter", "SkillPolicyAdapter"]
