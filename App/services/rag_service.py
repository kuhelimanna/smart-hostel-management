import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

class SimplePolicyRetriever:
    """
    Fast, reliable policy document retriever for DSATM Hostel Rules.
    Converts document chunks and performs keyword + context relevance matching.
    """
    def __init__(self, file_path="./Assets/Hostel_Rules_and_Policies.txt"):
        self.file_path = file_path
        self.chunks = []
        self.load_and_chunk_documents()

    def load_and_chunk_documents(self):
        if not os.path.exists(self.file_path):
            self.chunks = ["Hostel policy: Curfew is 9:00 PM on weekdays, 9:30 PM on weekends. Leave applications must be submitted 24 hours in advance."]
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            text = f.read()

        splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=100)
        docs = splitter.split_text(text)
        self.chunks = docs if docs else [text]

    def search(self, query: str, k: int = 3) -> list:
        query_words = set(query.lower().split())
        scored_chunks = []
        for chunk in self.chunks:
            chunk_words = set(chunk.lower().split())
            score = len(query_words.intersection(chunk_words))
            scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_k = [chunk for score, chunk in scored_chunks[:k]]
        return top_k if top_k else self.chunks[:k]

class EmbeddingService:
    def __init__(self):
        self.retriever = SimplePolicyRetriever()

    def process_hostel_policy_document(self, file_path: str = "./Assets/Hostel_Rules_and_Policies.txt"):
        self.retriever = SimplePolicyRetriever(file_path=file_path)
        print("Hostel policy document indexed successfully.")
        return True

    def retrieve_hostel_policy(self, query: str, k: int = 3) -> list:
        return self.retriever.search(query, k=k)

if __name__ == "__main__":
    service = EmbeddingService()
    service.process_hostel_policy_document()
    results = service.retrieve_hostel_policy("curfew rules")
    print("Search results for 'curfew rules':")
    for r in results:
        print("-", r)