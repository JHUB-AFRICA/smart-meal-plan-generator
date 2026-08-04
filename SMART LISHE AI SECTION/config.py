"""
config.py
------------------------------------

Central configuration file
for Smart Lishe AI.

Author:
    Hadassah Abigail
"""

# -----------------------------
# EMBEDDING MODEL
# -----------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

EMBEDDING_SIZE = 384

# -----------------------------
# QDRANT
# -----------------------------

QDRANT_HOST = "localhost"

QDRANT_PORT = 6333

COLLECTION_NAME = "nutrition_knowledge"

# -----------------------------
# LLM
# -----------------------------

LLM_MODEL = "EleutherAI/gpt-neo-125M"

# -----------------------------
# SEARCH
# -----------------------------

TOP_K_RESULTS = 5