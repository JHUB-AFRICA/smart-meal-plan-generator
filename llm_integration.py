"""
llm_integration.py
------------------------------------

Purpose:
    Generate AI responses using GPT-Neo
    and retrieved nutrition context.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from transformers import pipeline
from config import LLM_MODEL


class LLMIntegration:
    """
    Handles interaction with the language model.
    """

    def __init__(self):

        print("Loading Language Model...")

        self.generator = pipeline(
            task="text-generation",
            model=LLM_MODEL
        )

        print("Language Model Loaded Successfully!")

    def build_prompt(self, question, context):
        """
        Build the prompt sent to the language model.
        """

        prompt = f"""
You are Smart Lishe AI.

You are a professional nutrition assistant.

Use ONLY the information in the context.

If the answer cannot be found,
say you do not have enough information.

Context:

{context}

Question:

{question}

Answer:
"""

        return prompt

    def generate_response(
        self,
        question,
        context
    ):
        """
        Generate a response using GPT-Neo.
        """

        prompt = self.build_prompt(
            question,
            context
        )

        response = self.generator(

            prompt,

            max_new_tokens=150,

            temperature=0.3,

            do_sample=True

        )

        answer = response[0]["generated_text"]

        return answer


def main():

    llm = LLMIntegration()

    context = """
Eggs are high in protein.
Protein helps increase satiety.
Boiled eggs contain about 155 kcal per 100 g.
"""

    question = "Can I eat eggs while trying to lose weight?"

    answer = llm.generate_response(
        question,
        context
    )

    print(answer)


if __name__ == "__main__":

    main()