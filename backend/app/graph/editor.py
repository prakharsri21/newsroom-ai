from langfuse import observe

from app.graph.editor_agent import editor_agent_node
from app.graph.state import NewsroomState


@observe(
    name="editor-node",
    as_type="span",
    capture_output=False,
)
async def editor_node(state: NewsroomState) -> dict:
    return await editor_agent_node(state)