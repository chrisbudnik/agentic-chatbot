from app.agents.registry import AGENTS
from app.agents.base import BaseAgent


def test_registry_contains_agents():
	assert isinstance(AGENTS, dict)
	assert "default" in AGENTS
	assert "dummy" in AGENTS


def test_registry_values_are_agents():
	for name, agent in AGENTS.items():
		assert isinstance(agent, BaseAgent)
		assert agent.name
