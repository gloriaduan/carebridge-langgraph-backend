from agent_flow.state import GraphState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage


def query_validation(state: GraphState) -> GraphState:
    query = state.get("query")

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = PromptTemplate(
        template="""Classify if this query is about community/social support services.

            VALID: Shelters, food banks, health clinics, mental health, housing, child care, senior services, crisis help, legal aid, job training, disability services, support for specific groups (indigenous, immigrants, veterans, etc.)

            INVALID: Restaurants, retail, entertainment, hotels, commercial businesses

            Query: "{query}"

            Answer: VALID or INVALID""",
        input_variables=["query"],
    )

    llm_with_prompt = prompt | model

    output = llm_with_prompt.invoke({"query": query})

    print(f"Validation output: {output.content}")

    messages = state.get("messages") or []
    messages.append(AIMessage("Finished validating query"))

    return {"messages": messages, "is_valid_query": output.content}
