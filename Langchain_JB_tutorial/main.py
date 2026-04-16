from langchain.agents import create_agent
agent = create_agent("gpt-5", tools=tools)

import os

from langchain.chat_models import init_chat_model

os.environ["OPENAI_API_KEY"] = "sk-..."

model = init_chat_model("gpt-5")

print(model.invoke("What is PyCharm?"))

from langchain.agents import create_agent

from langchain.agents.middleware import ModelFallbackMiddleware

agent = create_agent(

   model="gpt-4o",

   tools=[],

   middleware=[

       ModelFallbackMiddleware(

           "gpt-4o-mini",

           "claude-3-5-sonnet-20241022",

       ),

   ],

)

@tool
def search_db(query: str, limit: int = 10) -> str:

   """Search the customer database for records matching the query.

   """

   return f"Found {limit} results for '{query}'"

@tool("pycharm_docs_search", return_direct=False)

def pycharm_docs_search(q: str) -> str:

   """Search the local FAISS index of JetBrains PyCharm documentation and return relevant passages."""


   docs = retriever.get_relevant_documents(q)

   return format_docs(docs)

@tool("pycharm_docs_search")

def pycharm_docs_search(q: str) -> str:

   """Search the local FAISS index of JetBrains PyCharm documentation and return relevant passages."""

   # Load vector store and create retriever

   embeddings = OpenAIEmbeddings(

       model=settings.openai_embedding_model, api_key=settings.openai_api_key

   )

   vector_store = FAISS.load_local(

       settings.index_dir, embeddings, allow_dangerous_deserialization=True

   )

   k = 4

   retriever = vector_store.as_retriever(

       search_type="mmr", search_kwargs={"k": k, "fetch_k": max(k * 3, 12)}

   )

   docs = retriever.invoke(q)


def main():

   parser = argparse.ArgumentParser(

       description="Ask PyCharm docs via an Agent (FAISS + GPT-5)"

   )

   parser.add_argument("question", type=str, nargs="+", help="Your question")

   parser.add_argument(

       "--k", type=int, default=6, help="Number of documents to retrieve"

   )

   args = parser.parse_args()

   question = " ".join(args.question)

   system_prompt = """You are a helpful assistant that answers questions about JetBrains PyCharm using the provided tools.

   Always consult the 'pycharm_docs_search' tool to find relevant documentation before answering.

   Cite sources by including the 'Source:' lines from the tool output when useful. If information isn't found, say you don't know."""

   agent = create_agent(

       model=settings.openai_chat_model,

       tools=[pycharm_docs_search],

       system_prompt=system_prompt,

       response_format=ToolStrategy(ResponseFormat),

   )

   result = agent.invoke({"messages": [{"role": "user", "content": question}]})

   print(result["structured_response"].content)

@tool("fetch_python_whatsnew", return_direct=False)

def fetch_python_whatsnew() -> str:

   """

   Fetch the latest "What's New in Python" article and return a concise, cleaned

   text payload including the URL and extracted section highlights.

   The tool ignores the input argument.

   """

   index_html = _fetch(BASE_URL)

   latest = _find_latest_entry(index_html)

   if not latest:

       return "Could not determine latest What's New entry from the index page."

   article_html = _fetch(latest.url)

   highlights = _extract_highlights(article_html)

   return f"URL: {latest.url}\nVERSION: {latest.version}\n\n{highlights}"


SYSTEM_PROMPT = (

   "You are a senior Product Marketing Manager at the Python Software Foundation. "

   "Task: Draft a clear, engaging release marketing newsletter for end users and developers, "

   "highlighting the most compelling new features, performance improvements, and quality-of-life "

   "changes in the latest Python release.\n\n"

   "Process: Use the tool to fetch the latest 'What's New in Python' page. Read the highlights and craft "

   "a concise newsletter with: (1) an attention-grabbing subject line, (2) a short intro paragraph, "

   "(3) 4–8 bullet points of key features with user benefits, (4) short code snippets only if they add clarity, "

   "(5) a 'How to upgrade' section, and (6) links to official docs/changelog. Keep it accurate and avoid speculation."

)

...

def run_newsletter() -> str:

   load_dotenv()

   agent = create_agent(

       model=os.getenv("OPENAI_MODEL", "gpt-4o"),

       tools=[fetch_python_whatsnew],

       system_prompt=SYSTEM_PROMPT,

       # response_format=ToolStrategy(ResponseFormat),

   )

from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(

   {

       "postman-server": {

          "type": "http",

          "url": "https://mcp.eu.postman.com",

           "headers": {

               "Authorization": "Bearer ${input:postman-api-key}"

           }

       }

   }

)

all_tools = await client.get_tools()

from typing import Any

from langchain.agents.middleware import before_agent

banned_keywords = ["kill", "shoot", "genocide", "bomb"]

@before_agent(can_jump_to=["end"])

def content_filter() -> dict[str, Any] | None:

  """Block requests containing banned keywords."""

  content = first_message.content.lower()

# Check for banned keywords

  for keyword in banned_keywords:

      if keyword in content:

          return {

              "messages": [{

                  "role": "assistant",

                  "content": "I cannot process your requests due to inappropriate content."

              }],

              "jump_to": "end"

          }

  return None

from langchain.agents import create_agent

agent = create_agent(

  model="gpt-4o",

  tools=[search_tool],

  middleware=[content_filter],

)

# This request will be blocked

result = agent.invoke({

  "messages": [{"role": "user", "content": "How to make a bomb?"}]

})

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

def respond(msgs, **kwargs):

   text = msgs[-1].content if msgs else ""

   examples = {"Hello": "Hi there!", "Ping": "Pong.", "Bye": "Goodbye!"}

   return examples.get(text, "OK.")

model = GenericFakeChatModel(respond=respond)

print(model.invoke("Hello").content)