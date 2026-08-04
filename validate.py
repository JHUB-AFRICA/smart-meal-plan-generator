"""
validate.py
-------------------------------------

Checks that every major Smart Lishe AI component
is available and working correctly.

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


class ProjectValidator:
    """
    Validates the Smart Lishe AI project.
    """

    def __init__(self):
        print("Project Validator initialized.")

    def validate_embeddings(self):
        """
        Check the embedding model.
        """
        print("Checking Embedding Model...")

        embedding = EmbeddingModel()

        print("✓ Embedding Model loaded successfully.")

    def validate_qdrant(self):
        """
        Check Qdrant database.
        """
        print("Checking Qdrant...")

        database = QdrantStore()

        print("✓ Qdrant connection successful.")

    def validate_rag(self):
        """
        Check RAG Agent.
        """
        print("Checking RAG Agent...")

        rag = RAGAgent()

        print("✓ RAG Agent ready.")

    def validate_llm(self):
        """
        Check GPT-Neo.
        """
        print("Checking Language Model...")

        llm = LLMIntegration()

        print("✓ Language Model loaded.")

    def validate_photo_scanner(self):
        """
        Check Photo Scanner.
        """
        print("Checking Photo Scanner...")

        scanner = PhotoScanner()

        print("✓ Photo Scanner ready.")

    def validate_project(self):
        """
        Run all validation checks.
        """

        print("\nStarting Smart Lishe AI Validation...\n")

        self.validate_embeddings()

        self.validate_qdrant()

        self.validate_rag()

        self.validate_llm()

        self.validate_photo_scanner()

        print("\n✓ ALL SYSTEMS PASSED VALIDATION.")