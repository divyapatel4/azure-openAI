import azure.functions
from dotenv import load_dotenv
load_dotenv()

import os
from utilities.helper import LLMHelper

def main(req: azure.functions.HttpRequest) -> str:
    # Get data from POST request
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        question = req_body.get("question")
        history = req_body.get("history", [])
        custom_prompt = req_body.get("custom_prompt", "")
        custom_temperature = float(req_body.get("custom_temperature", os.getenv("OPENAI_TEMPERATURE", 0.7)))
        index = req_body.get("index")
        query_type = req_body.get("query_type","vector")
        
    # Create LLMHelper object
    llm_helper = LLMHelper(custom_prompt=custom_prompt, temperature=custom_temperature)
    # Get answer
    data = {}
    if query_type == "vector":
        data["question"], data["response"], data["context"], data["sources"] = llm_helper.get_semantic_answer_lang_chain(question,index, history)
    else:
        data["question"], data["response"], data["context"], data["sources"] = llm_helper.get_semantic_answer_lang_chain_exp(question,index, history)
    
    ## LOG-D output sem-t
    
    # Return answer
    return f'{data}'