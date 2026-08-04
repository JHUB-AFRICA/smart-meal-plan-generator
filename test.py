"""
test.py
-------------------------------------

Tests individual Smart Lishe AI modules.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from embeddings import EmbeddingModel
from qdrant_store import QdrantStore
from rag_agent import RAGAgent
from llm_integration import LLMIntegration
from photo_scan import PhotoScanner


class ProjectTester:
    """
    Runs simple tests on all project modules.
    """

    def __init__(self):
        print("Project Tester initialized.")

    def test_embeddings(self):
        """
        Test the embedding model.
        """

        print("\nTesting Embedding Model...")

        embedding = EmbeddingModel()

        sample_text = "Rice contains carbohydrates."

        vector = embedding.create_embedding(sample_text)

        if vector is not None:
            print("✓ Embedding Test Passed")
        else:
            print("❌ Embedding Test Failed")

    def test_qdrant(self):
        """
        Test Qdrant initialization.
        """

        print("\nTesting Qdrant...")

        database = QdrantStore()

        print("✓ Qdrant Test Passed")

    def test_rag(self):
        """
        Test the RAG Agent.
        """

        print("\nTesting RAG Agent...")

        rag = RAGAgent()

        print("✓ RAG Test Passed")

    def test_llm(self):
        """
        Test the Language Model.
        """

        print("\nTesting Language Model...")

        llm = LLMIntegration()

        print("✓ LLM Test Passed")

    def test_photo_scanner(self):
        """
        Test the Photo Scanner.
        """

        print("\nTesting Photo Scanner...")

        scanner = PhotoScanner()

        print("✓ Photo Scanner Test Passed")

    def run_all_tests(self):
        """
        Run every project test.
        """

        print("\n==============================")
        print("SMART LISHE AI TEST SUITE")
        print("==============================")

        self.test_embeddings()
        self.test_qdrant()
        self.test_rag()
        self.test_llm()
        self.test_photo_scanner()

        print("\n==============================")
        print("ALL TESTS COMPLETED")
        print("==============================")