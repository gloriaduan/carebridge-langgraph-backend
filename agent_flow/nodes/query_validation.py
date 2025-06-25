from agent_flow.state import GraphState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage


def query_validation(state: GraphState) -> GraphState:
    query = state.get("query")

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = PromptTemplate(
        template="""You are a classifier that checks if a user query is about community support services.

            Valid topics include:
            - Shelters
            - Food banks
            - Community centers
            - Free clinics
            - Mental health support
            - Public housing
            - Crisis or social services

            Examples of VALID queries:
            - “Find a food bank near me”
            - “Where is the nearest shelter?”
            - “I need free mental health support”

            Examples of INVALID queries:
            - “Best pizza nearby”
            - “Starbucks hours”
            - “Hotels in Toronto”

            Classify this query:

            "{query}"

            Respond only with: VALID or INVALID""",
        input_variables=["query"],
    )

    llm_with_prompt = prompt | model

    output = llm_with_prompt.invoke({"query": query})

    messages = state.get("messages") or []
    messages.append(AIMessage("Finished validating query"))

    return {"messages": messages, "is_valid_query": output.content}
