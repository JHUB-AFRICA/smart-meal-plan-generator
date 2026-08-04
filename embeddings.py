"""
embeddings.py
------------------------------------

Purpose:
    Load the Sentence Transformer embedding model and convert
    text into numerical vectors (embeddings).

Model Used:
    sentence-transformers/all-MiniLM-L6-v2

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

class EmbeddingModel:
    """
    Handles loading the embedding model and creating embeddings.
    """

    def __init__(self):
        """
        Load the embedding model only once when the class is created.
        """

        print("Loading embedding model...")

        self.model = SentenceTransformer(
            EMBEDDING_MODEL
        )

        print("Embedding model loaded successfully!")

    def encode_text(self, text):
        """
        Convert text into an embedding vector.

        Parameters
        ----------
        text : str
            Text that will be converted into an embedding.

        Returns
        -------
        list
            Numerical embedding vector.
        """

        embedding = self.model.encode(text)

        return embedding


def main():
    """
    Test the embedding model.
    """

    model = EmbeddingModel()

    sample_text = "Chicken is a good source of protein."

    vector = model.encode_text(sample_text)

    print("\nOriginal Text:")
    print(sample_text)

    print("\nEmbedding Length:")
    print(len(vector))

    print("\nFirst 10 Values:")
    print(vector[:10])


if __name__ == "__main__":
    main()