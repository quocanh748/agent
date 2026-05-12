from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_experimental.text_splitter import SemanticChunker
import os

class AIAgent:
    def __init__(self, db_path="./Database", model_name="qwen2.5:1.5b"):
        self.db_path = db_path
        self.model_name = model_name
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-base",
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': False}
        )
        self.vectorstore = None
        self.rag_chain = None
        self.setup()

    def setup(self):
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            print(f"Created {self.db_path} directory. Please add PDFs there.")
            # Create a placeholder chain if no docs exist
            self._setup_simple_chain()
            return

        loader = DirectoryLoader(
            path=self.db_path,
            glob="**/*.pdf",
            loader_cls=UnstructuredFileLoader,
            show_progress=True,
            use_multithreading=True
        )

        docs = loader.load()
        
        if not docs:
            print("No documents found in Database. Using simple LLM mode.")
            self._setup_simple_chain()
            return

        text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold=0.5
        )
        splits = text_splitter.split_documents(docs)

        self.vectorstore = FAISS.from_documents(
            documents=splits,
            embedding=self.embeddings,
            distance_strategy=DistanceStrategy.COSINE
        )

        retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 5, "score_threshold": 0.3}
        )

        prompt = ChatPromptTemplate.from_template("""
            You are a professional and helpful AI Assistant.
            
            Answer the question based on the context provided. If you don't know, just say you don't know.
            
            Context: {context}
            Question: {question}
            
            Answer in the same language as the question.
        """)

        llm = OllamaLLM(
            model=self.model_name,
            temperature=0.7
        )

        self.rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

    def _setup_simple_chain(self):
        prompt = ChatPromptTemplate.from_template("""
            You are a professional and helpful AI Assistant.
            Question: {question}
        """)
        llm = OllamaLLM(
            model=self.model_name,
            temperature=0.7
        )
        self.rag_chain = (
            {"question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

    def ask(self, question: str):
        if not self.rag_chain:
            return "Agent not initialized properly."
        return self.rag_chain.invoke(question)
