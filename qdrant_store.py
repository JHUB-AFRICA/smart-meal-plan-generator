"""
qdrant_store.py
------------------------------------

Purpose:
    Store and retrieve embeddings from Qdrant.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)

from config import (
    QDRANT_HOST,
    QDRANT_PORT,
    COLLECTION_NAME,
    EMBEDDING_SIZE
)


class QdrantStore:
    """
    Handles all communication with Qdrant.
    """

    def __init__(self):

        print("Connecting to Qdrant...")

        self.client = QdrantClient(
            host="QDRANT_HOST",
            port= QDRANT_PORT
        )

        self.collection_name = "COLLECTION_NAME"

        print("Connected successfully!")

    def create_collection(self):
        """
        Create the vector collection if it doesn't already exist.
        """

        collections = self.client.get_collections()

        existing = [
            collection.name
            for collection in collections.collections
        ]

        if self.collection_name not in existing:

            self.client.create_collection(
                collection_name=self.collection_name,

                vectors_config=VectorParams(
                    size= EMBEDDING_SIZE,
                    distance=Distance.COSINE
                )
            )

            print("Collection created.")

        else:

            print("Collection already exists.")

    def insert_document(
        self,
        document_id,
        embedding,
        text
    ):
        """
        Store one document.
        """

        self.client.upsert(

            collection_name=self.collection_name,

            points=[

                PointStruct(

                    id=document_id,

                    vector=embedding,

                    payload={
                        "text": text
                    }

                )

            ]

        )

        print(f"Document {document_id} stored successfully.")

    def search(
        self,
        query_embedding,
        limit=5
    ):
        """
        Search for similar documents.
        """

        results = self.client.search(

            collection_name=self.collection_name,

            query_vector=query_embedding,

            limit=limit

        )

        return results


def main():

    database = QdrantStore()

    database.create_collection()


if __name__ == "__main__":

    main()