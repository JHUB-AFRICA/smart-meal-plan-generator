"""
download_model.py
-------------------------------------

Downloads all AI models required by
Smart Lishe AI.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder
from transformers import AutoTokenizer
from transformers import AutoModelForCausalLM


class ModelDownloader:

    def __init__(self):

        print("Smart Lishe AI Model Downloader\n")

    def download_embedding_model(self):

        print("Downloading Embedding Model...")

        SentenceTransformer("all-MiniLM-L6-v2")

        print("✓ Embedding Model downloaded.\n")

    def download_cross_encoder(self):

        print("Downloading Cross Encoder...")

        CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        print("✓ Cross Encoder downloaded.\n")

    def download_gpt_neo(self):

        print("Downloading GPT-Neo...")

        tokenizer = AutoTokenizer.from_pretrained(
            "EleutherAI/gpt-neo-125M"
        )

        model = AutoModelForCausalLM.from_pretrained(
            "EleutherAI/gpt-neo-125M"
        )

        print("✓ GPT-Neo downloaded.\n")

    def download_all(self):

        self.download_embedding_model()

        self.download_cross_encoder()

        self.download_gpt_neo()

        print("--------------------------------")
        print("ALL MODELS DOWNLOADED")
        print("--------------------------------")


if __name__ == "__main__":

    downloader = ModelDownloader()

    downloader.download_all()