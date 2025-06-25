from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage
from agent_flow.models.responses import AgentResponse
from agent_flow.state import GraphState


def generate_final_response(state: GraphState) -> Dict[str, Any]:
    print("GENERATING FINAL RESPONSE...")

    if state.get("is_valid_query") != "VALID":
        print("Query is invalid, skipping final response generation.")
        return {
            "messages": state.get("messages", []),
            "structured_response": None,
            "error_response": "Sorry! Please try again with a different query.",
        }

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    parser = PydanticOutputParser(pydantic_object=AgentResponse)

    prompt = PromptTemplate(
        template="""Retrieved results: {results} \n
            ONLY based on the above results, provide information in the following JSON format:
            {format_instructions}
            Ensure the output is a valid JSON object that matches the schema exactly. Do not include any additional text or explanations.""",
        input_variables=["results"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    llm_with_parser = prompt | model | parser

    if state.get("use_search"):
        results = state.get("search_results")
    else:
        results = state.get("api_results")

    output = llm_with_parser.invoke({"results": results})

    messages = state.get("messages") or []
    messages.append(AIMessage("Finished generating response"))

    return {"messages": messages, "structured_response": output}
