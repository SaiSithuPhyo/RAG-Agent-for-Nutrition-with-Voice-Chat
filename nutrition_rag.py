import os
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

api_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Integrating with LangChain
# RAG
# Integrate with Vector Stores
persist_directory = 'db'
vector_store_exists = os.path.exists(persist_directory)

# Set up embeddings model
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

if vector_store_exists:
    # Load the vector store if it already exists
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
else:
    # Load data and create vector store if it doesn't exist
    loader = DirectoryLoader('Nutrition Data', glob='./*.pdf', loader_cls=PyPDFLoader)
    raw_data = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    nutrition_data = text_splitter.split_documents(raw_data)
    
    vectordb = Chroma.from_documents(documents=nutrition_data, 
                                     embedding=embeddings,
                                     persist_directory=persist_directory)

retriever = vectordb.as_retriever(search_kwargs={"k":5})  # Retrieve top 5

#Retrieval QA
llm = ChatGoogleGenerativeAI(model='gemini-1.5-pro', temperature=0.7)

memory = ConversationBufferMemory(memory_key="chat_history")

# Set up RetrievalQA with memory context
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    memory = memory,
    return_source_documents=False
)

## Cite sources

import textwrap

def wrap_text_preserve_newlines(text, width=110):
    # Split the input text into lines based on newline characters
    lines = text.split('\n')

    # Wrap each line individually
    wrapped_lines = [textwrap.fill(line, width=width) for line in lines]

    # Join the wrapped lines back together using newline characters
    wrapped_text = '\n'.join(wrapped_lines)

    return wrapped_text

def process_llm_response(llm_response):
    final_response = wrap_text_preserve_newlines(llm_response['result'])
    return final_response

# To call the RAG agent
def call_rag_agent(query):
    # Retrieve memory history and append it to the query to retain conversational context
    conversation_history = memory.load_memory_variables({})["chat_history"]
    modified_query = f"{conversation_history}\n\nUser: {query}"

    response = qa_chain.invoke(modified_query)
    final_response = process_llm_response(response)
    return final_response

#testing


# Chat Memory Test
print(call_rag_agent("Hello, my name is Lin. My favorite food is pizza."))
print(call_rag_agent("Can you tell me how many letters are there in my favorite food?"))


# Retrieval QA Test
print(call_rag_agent("Tell me the ingredients of pumpkin bites."))
print(call_rag_agent("Tell me about Tell me about amount of calories needed for people?"))
print(call_rag_agent("Can you tel me about pre-workout meals?"))
