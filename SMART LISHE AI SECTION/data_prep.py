"""
data_prep.py
------------------------------------

Purpose:
    Read nutrition datasets, clean them, and prepare
    documents for embedding.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

import pandas as pd


class DataPreparation:
    """
    Handles loading and preparing nutrition data.
    """

    def __init__(self):

        print("Data Preparation Module Initialized.")

    def load_csv(self, file_path):
        """
        Load a CSV file into a pandas DataFrame.
        """

        dataframe = pd.read_csv(file_path)

        print(f"Loaded {len(dataframe)} records.")

        return dataframe

    def clean_data(self, dataframe):
        """
        Basic cleaning of the dataset.
        """

        dataframe = dataframe.drop_duplicates()

        dataframe = dataframe.fillna("Unknown")

        return dataframe

    def create_documents(self, dataframe):
        """
        Convert each row into one text document.
        """

        documents = []

        for _, row in dataframe.iterrows():

            text = " | ".join(
                f"{column}: {row[column]}"
                for column in dataframe.columns
            )

            documents.append(text)

        return documents


def main():

    print("Data Preparation Module Ready.")


if __name__ == "__main__":
    main()