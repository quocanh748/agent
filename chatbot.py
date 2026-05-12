from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_experimental.text_splitter import SemanticChunker

def rag_chatbot():

    loader = DirectoryLoader(
        path = "./Database",
        glob = "**/*.pdf",
        loader_cls=UnstructuredFileLoader,
        show_progress=True,
        use_multithreading=True
    )

    docs = loader.load()

    print(len(docs))

    MARKDOWN_SEPARATORS = [
        "#",    
        "##",
        "###",
        "####",
        "#####",
        "******",
        "***",
        "_",
        "\n"
    ]

    # text_splitter = RecursiveCharacterTextSplitter(
    #     chunk_size = 1000,
    #     chunk_overlap = 200,
    #     add_start_index=True,
    #     strip_whitespace=True,
    #     separators = MARKDOWN_SEPARATORS,
    # )

    text_splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold=0.5
    )

    splits = text_splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(

        model_name="intfloat/multilingual-e5-base",
        # model_name="sentence-transformers/all-MiniLM-L6-v2"
            
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': False}
    )

    vectorstore = FAISS.from_documents(
        documents=splits,
        embedding=embeddings,
        distance_strategy=DistanceStrategy.COSINE
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k":10, "score_threshold": 0.3}
    )

    prompt = ChatPromptTemplate.from_template("""
        You are a funny expert in Computer Science, answer short.

        Just answer the question using the context, if you don't know the answer, say so.

        Do not use outside knowledge, guessing, or web information

        Context:{context}

        Question:{question}
    """)

    llm = OllamaLLM(
        model="qwen2.5:1.5b", 
        temperature=0.1    
    )

    rag_chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
    )

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break
        answer = rag_chain.invoke(user_input)
        print("Bot: ", answer)

if __name__ == "__main__":
    rag_chatbot()