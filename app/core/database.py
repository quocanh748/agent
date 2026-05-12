# app/core/database.py
import os
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

class VectorDBManager:
    def __init__(self, pdf_dir: str, persist_dir: str, embeddings):
        """
        Quản lý Vector Database (ChromaDB)
        :param pdf_dir: Thư mục chứa các file PDF gốc
        :param persist_dir: Thư mục lưu trữ database SQLite của Chroma
        :param embeddings: Mô hình Embedding (HuggingFace)
        """
        self.pdf_dir = pdf_dir
        self.persist_dir = persist_dir
        self.embeddings = embeddings
        self.vectorstore = None
        self._initialize_db()

    def _initialize_db(self):
        # 1. Kiểm tra thư mục PDF
        if not os.path.exists(self.pdf_dir):
            os.makedirs(self.pdf_dir)
            print(f"[Database] Created {self.pdf_dir} directory. Please add PDFs there.")
            return

        # 2. Nếu đã có DB trên ổ cứng thì chỉ cần kết nối lại
        if os.path.exists(self.persist_dir) and os.listdir(self.persist_dir):
            print(f"[Database] Loading existing Vector Database from {self.persist_dir}...")
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
        # 3. Nếu chưa có DB, tiến hành đọc PDF và nhúng (embed) mới
        else:
            print("[Database] No existing Vector DB found. Reading PDFs...")
            loader = DirectoryLoader(
                path=self.pdf_dir,
                glob="**/*.pdf",
                loader_cls=PyPDFLoader
            )
            docs = loader.load()
            
            if not docs:
                print("[Database] No documents found in folder.")
                return

            print("[Database] Chunking documents...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            splits = text_splitter.split_documents(docs)

            print("[Database] Creating and saving new Vector DB...")
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_dir
            )
            print(f"[Database] Vector Database saved successfully to {self.persist_dir}")

    def get_retriever(self, search_type="similarity", k=5):
        """
        Trả về đối tượng retriever để Agent tìm kiếm nội dung
        :param search_type: "similarity" hoặc "mmr"
        :param k: Số lượng đoạn văn bản tối đa trả về
        """
        if not self.vectorstore:
            return None
            
        return self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs={"k": k}
        )