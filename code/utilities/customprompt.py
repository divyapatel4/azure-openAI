from langchain.prompts import PromptTemplate


template = """ {summaries}
-------------------------------------------------
You are chatbot for Microsoft Cloud for Sustainability(MCfS) and you are answering questions about the MCfS.

Using the information provided above from the search, please answer to the user's question. The user is not aware of the information in the text above, so it is important to include all relevant details in your answer. 
Include references to the sources you used to create the answer if those are relevant ("SOURCES"). 

Question: {question}

Answer: 
"""

smes_template = """
{summaries}
-------------------------------------------------
Question: {question}

Answer: Please provide a detailed and thorough answer that addresses all aspects of the question. Make sure to include all relevant details from the information provided above.
THE USER CAN'T SEE THE TEXT ABOVE, SO PLEASE INCLUDE ALL RELEVANT DETAILS IN YOUR ANSWER.
ANSWER IN DETAIL and INCLUDE EMAIL OF EVERYONE.
"""


PROMPT = PromptTemplate(template=template, input_variables=["summaries", "question"])

SMES_PROMPT = PromptTemplate(template=smes_template, input_variables=["summaries", "question"])