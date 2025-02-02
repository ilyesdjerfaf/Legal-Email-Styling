"""
Utils functions for the project

@Authors : Ilyes DJERFAF, Nazim KESKES
"""

############################################
# Libraries
############################################

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re
import pickle
from typing import List, Tuple


############################################
# EDA Functions
############################################

def plot_na(data:pd.DataFrame) -> None:
    """
    Plot the missing values in the dataset

    Params:
        data (pd.DataFrame): Input dataset

    Returns:
        None
    """
    missing_percentage = data.isnull().mean() * 100  
    missing_count = data.isnull().sum()

    stats_sorted = missing_percentage.sort_values(ascending=False)
    counts_sorted = missing_count[stats_sorted.index]

    plt.figure(figsize=(12, 6))
    bars = plt.bar(stats_sorted.index, stats_sorted.values, color='skyblue')

    for bar, count in zip(bars, counts_sorted.values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(stats_sorted.values) * 0.01),
            f"{count:,}", 
            ha='center', va='bottom', fontsize=10
        )

    plt.title("Pourcentage de valeurs manquantes par colonne avec count", fontsize=16)
    plt.xlabel("Colonnes", fontsize=12)
    plt.ylabel("Pourcentage de valeurs manquantes (%)", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()


def keep_valid_senders(X) -> Tuple[List[str], List[str]]:
    """Keep only valid senders

    Params:
        X : list of senders
    
    Returns:
        List[str]: list of valid senders
        List[str]: list of valid enron senders
    """
    enron_senders = [sender for sender in X if 'enron' in sender.lower()]
    news_senders = [sender for sender in X if 'news' in sender.lower()]
    no_reply_senders = [sender for sender in X if 'no-reply' in sender.lower()]

    with open('not_enron_correct_mails.pkl', 'rb') as f:
        not_enron_correct_mails = pickle.load(f)
    
    concat_good_senders = enron_senders + not_enron_correct_mails
    concat_good_senders = [sender for sender in concat_good_senders if sender not in news_senders]
    concat_good_senders = [sender for sender in concat_good_senders if sender not in no_reply_senders]
    concat_good_senders = [sender for sender in concat_good_senders if "announcement" not in sender.lower()]
    
    # keep only enron senders that are like nom.prenom@enron.com only with a regex
    matching_re = re.compile(r'^[a-zA-Z]+(?:\.[a-zA-Z]+)?@enron\.com$')
    enron_valid = [sender for sender in concat_good_senders if matching_re.match(sender) is not None]
    return concat_good_senders, enron_valid


############################################
# Generating Users ID Functions
############################################