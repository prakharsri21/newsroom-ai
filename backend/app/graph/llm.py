from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.graph.tools.research_tools import search_news
from app.schemas.research import ResearchDecision
from app.schemas.editor import ArticleDraft

settings = get_settings()


researcher_llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    use_responses_api=True,
    output_version="responses/v1",
    reasoning={
        "effort": "low",
    },
).bind_tools([search_news])


researcher_decision_llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    use_responses_api=True,
    output_version="responses/v1",
    reasoning={
        "effort": "low",
    },
).with_structured_output(ResearchDecision)

editor_llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    use_responses_api=True,
    output_version="responses/v1",
    reasoning={"effort": "low"},
).with_structured_output(ArticleDraft)