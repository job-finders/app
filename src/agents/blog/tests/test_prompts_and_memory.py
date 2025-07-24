import pytest
from src.agents.blog.agent import TopicDiscoveryAgent, ArticlePlannerAgent
from src.agents.blog.memory import memory
from src.agents.blog.schemas import Topic


def test_prompt_renders_without_error():
    agent = TopicDiscoveryAgent()
    prompt = agent.render_system({
        "agent_type": "Test",
        "job_description": "test",
        "schema_json": Topic.schema_json(),
        "memory_keys": ["test:foo"]
    })
    assert "Blog-Agent-Test" in prompt


def test_memory_round_trip():
    memory.add_entry("user", "hello")
    msgs = memory.get_chat_messages(limit=1)
    assert msgs[-1]["content"] == "hello"