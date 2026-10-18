from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search , scrape_url 
from dotenv import load_dotenv
import os

load_dotenv(override=True)  # .env wins over stale shell variables

#model setup
# Works with OpenAI by default. For a free option such as Groq, set these in .env:
#   LLM_API_KEY=...  LLM_BASE_URL=https://api.groq.com/openai/v1  LLM_MODEL=openai/gpt-oss-120b
llm = ChatOpenAI(
    model = os.getenv("LLM_MODEL", "gpt-4o-mini"),
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("LLM_BASE_URL") or None,
    temperature=0,
)


#1st agent 
def build_search_agent():
    return create_agent(
        model = llm,
        tools= [web_search]
    )

#2nd agent 

def build_reader_agent():
    return create_agent(
        model = llm,
        tools = [scrape_url]
    )


#writer chain 

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()

#critic_chain 

critic_prompt = ChatPromptTemplate.from_messages([
     ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain = critic_prompt | llm | StrOutputParser()

