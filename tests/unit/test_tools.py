"""Unit tests for tool registry and guardrails."""

from procurement_ai.tools.registry import clear_tools, get_tool, list_tools, register_tool


class TestToolRegistry:
    def setup_method(self):
        clear_tools()

    def teardown_method(self):
        clear_tools()

    def test_register_tool(self):
        def sample_func():
            return "test"

        register_tool("sample_tool", "A sample tool", sample_func)
        tool = get_tool("sample_tool")
        assert tool is not None
        assert tool["name"] == "sample_tool"
        assert tool["description"] == "A sample tool"

    def test_list_tools(self):
        register_tool("tool1", "Tool 1", lambda: None)
        register_tool("tool2", "Tool 2", lambda: None)
        tools = list_tools()
        assert len(tools) == 2

    def test_get_nonexistent_tool(self):
        result = get_tool("nonexistent")
        assert result is None
