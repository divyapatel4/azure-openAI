from langchain.prompts import PromptTemplate

# template = """{summaries}
# Please reply to the question using the information present in the text above. 
# Include references to the sources you used to create the answer if those are relevant ("SOURCES"). 
# If you can't find it, try to answer it telling that you need more context but this is the answer as per your understanding else reply politely that the information is not in the knowledge base.
# Question: {question}
# Answer:"""

template = """ {summaries}
-------------------------------------------------
Using the information provided above from the search engine, please provide a detailed and comprehensive answer to the user's question. The user is not aware of the information in the text above, so it is important to include all relevant details in your answer. 
Include references to the sources you used to create the answer if those are relevant ("SOURCES"). 

Question: {question}

Answer: Please provide a detailed and thorough answer that addresses all aspects of the question. Your goal is to provide the user with as much information as possible to help them understand the topic at hand. Include all necessary details and references in your answer.
ANSWER IN EXTREME DETAIL
"""

smes_template = """
{summaries}
-------------------------------------------------
As a sustainability chatbot, it is your responsibility to provide a detailed and comprehensive response to the user's question using the information provided above from the search engine. The user is not aware of the information in the text above, so it is important to include all relevant details and contact information if applicable in your answer.

Question: {question}

Answer: Please provide a detailed and thorough answer that addresses all aspects of the question and includes any relevant contact information. Your goal is to provide the user with as much information as possible to help them understand the topic at hand. Include all necessary details and references in your answer.
ANSWER IN EXTREME DETAIL
"""


PROMPT = PromptTemplate(template=template, input_variables=["summaries", "question"])
SMES_PROMPT = PromptTemplate(template=smes_template, input_variables=["summaries", "question"])