from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

loader = PyPDFLoader("doc.pdf")
docs = loader.load()
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents(docs)

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)

from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

llm = ChatOpenAI(
    temperature=0,
    model="gpt-4o-mini"
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
    return_source_documents=False
)

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
class QuestionRequest(BaseModel):
    question: str

@app.post("/ask")
def ask_question(req: QuestionRequest):
    result = qa_chain.run(req.question)
    return {"answer": result}