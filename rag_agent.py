"""
rag_agent.py
------------------------------------

Purpose:
    Coordinate the Retrieval-Augmented Generation (RAG)
    workflow.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from embeddings import EmbeddingModel
from qdrant_store import QdrantStore
from config import TOP_K_RESULTS

class RAGAgent:
    """
    Coordinates the retrieval pipeline.
    """

    def __init__(self):

        print("Initializing RAG Agent...")

        self.embedding_model = EmbeddingModel()

        self.database = QdrantStore()

        print("RAG Agent Ready!")

    def retrieve_documents(
        self,
        user_question,
        limit= TOP_K_RESULTS
    ):
        """
        Retrieve the most relevant documents
        from Qdrant.
        """

        print("\nCreating embedding...")

        question_vector = self.embedding_model.encode_text(
            user_question
        )

        print("Searching Qdrant...")

        results = self.database.search(
            query_embedding=question_vector,
            limit=limit
        )

        return results


def main():

    rag = RAGAgent()

    question = "Can I eat rice if I have diabetes?"

    results = rag.retrieve_documents(question)

    print(results)


if __name__ == "__main__":

    main()