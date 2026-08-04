"""
main.py
------------------------------------

Main entry point for Smart Lishe AI.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from rag_agent import RAGAgent
from llm_integration import LLMIntegration


def main():
    """
    Run the Smart Lishe AI chatbot.
    """

    print("=" * 50)
    print("🥗 Welcome to Smart Lishe AI")
    print("=" * 50)

    # Initialize the AI components
    rag = RAGAgent()
    llm = LLMIntegration()

    while True:
        print()
        question = input("Ask a nutrition question (or type 'exit'): ")

        if question.lower() == "exit":
            print("Goodbye! 👋")
            break

        print("\nSearching nutrition database...")

        # Retrieve relevant information
        context = rag.retrieve(question)

        print("Generating response...\n")

        # Generate the final answer
        answer = llm.generate_response(question, context)

        print("=" * 50)
        print("Smart Lishe AI")
        print("=" * 50)
        print(answer)


if __name__ == "__main__":
    main()