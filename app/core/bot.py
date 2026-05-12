# app/core/bot.py
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# IMPORT MODULE DATABASE MỚI TẠO
from app.core.database import VectorDBManager

class AIAgent:
    def __init__(self, pdf_dir="./Database", persist_dir="./VectorDB", model_name="qwen2.5:1.5b"):
        self.model_name = model_name
        self.store = {}
        
        # 1. Khởi tạo model Embedding
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-base",
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': False}
        )
        
        # 2. GỌI MODULE DATABASE
        self.db_manager = VectorDBManager(
            pdf_dir=pdf_dir, 
            persist_dir=persist_dir, 
            embeddings=self.embeddings
        )
        
        self.rag_chain = None
        self.setup()

    def get_session_history(self, session_id: str):
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    def setup(self):
        # Lấy retriever từ module database
        retriever = self.db_manager.get_retriever()

        # Nếu không có retriever (do chưa có PDF), tự động chuyển về chế độ chat thông thường
        if not retriever:
            print("[Agent] No Vector DB available. Using simple LLM mode.")
            self._setup_simple_chain()
            return

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional and helpful AI Assistant.
            Answer the question based on the context provided. If you don't know, just say you don't know.
            
            Context: {context}"""),
            MessagesPlaceholder(variable_name="chat_history"), 
            ("human", "{question}")
        ])

        llm = OllamaLLM(
            model=self.model_name,
            temperature=0.7
        )

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        base_chain = (
            RunnablePassthrough.assign(
                context=lambda x: format_docs(retriever.invoke(x["question"]))
            )
            | prompt
            | llm
            | StrOutputParser()
        )

        self.rag_chain = RunnableWithMessageHistory(
            base_chain,
            self.get_session_history,
            input_messages_key="question",
            history_messages_key="chat_history"
        )

    def _setup_simple_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional and helpful AI Assistant."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        llm = OllamaLLM(model=self.model_name, temperature=0.7)
        
        base_chain = prompt | llm | StrOutputParser()
        
        self.rag_chain = RunnableWithMessageHistory(
            base_chain,
            self.get_session_history,
            input_messages_key="question",
            history_messages_key="chat_history"
        )

    def ask(self, question: str, session_id: str = "default_user"):
        if not self.rag_chain:
            return "Agent not initialized properly."
        
        return self.rag_chain.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}}
        )