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
import json
import spacy
import nltk
import statistics
import pandas as pd
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from collections import Counter
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI

############################################
# Configuration
############################################

# Télécharge les ressources NLTK
nltk.download('punkt')
nltk.download('stopwords')
from nltk.corpus import stopwords

# Charge SpaCy
nlp = spacy.load("en_core_web_lg")

# Pipeline de sentiment (exemple)
sentiment_classifier = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment"
)

# Embeddings
style_embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Chargement variables d’environnement
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Configuration du LLM Llama-3
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    openai_api_key=api_key,
    temperature=0.0
)


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

########################################################################
# 1. Tone Classification (Formality, Emotion, Attitude)
########################################################################

def classify_formality_llama(text):
    """
    Detects whether the text is FORMAL or INFORMAL using Llama-3.
    """
    system_prompt = """You are an expert linguist.
    Classify an email as either "FORMAL" or "INFORMAL" based on:
    - FORMAL: Polite, professional, no slang, well-structured.
    - INFORMAL: Casual language, slang, contractions, personal style.
    Respond ONLY with "FORMAL" or "INFORMAL".
    """
    user_prompt = f"Email:\n{text}\n"

    response = llm.invoke([
        ("system", system_prompt),
        ("human", user_prompt)
    ])
    label = response.content.strip().upper()
    if label not in ["FORMAL", "INFORMAL"]:
        label = "FORMAL"
    return label

def detect_emotion(text):
    """
    'emotional' si sentiment extrême (1 star / 5 stars), sinon 'neutral'.
    """
    result = sentiment_classifier(text[:512])[0]
    label = result['label']  # e.g., "1 star", "2 stars", ...
    if label in ["1 star", "5 stars"]:
        return "emotional"
    else:
        return "neutral"

def detect_attitude(text):
    """
    'assertive' vs 'attenuated' selon la fréquence de modaux comme could/would.
    """
    doc = nlp(text)
    modals = {"could", "would", "might", "maybe", "perhaps"}
    modal_count = sum(1 for token in doc if token.text.lower() in modals)

    ratio_modals = modal_count / (len(doc) + 1e-9)
    if ratio_modals > 0.02:
        return "attenuated"
    else:
        return "assertive"

########################################################################
# 2. Vocabulary
########################################################################

def measure_vocabulary(emails):
    """
    - Word type => 'sophisticated' vs 'common' (via avg word length)
    - Lexical richness (TTR)
    - Jargon presence
    """
    full_text = " ".join(emails)
    doc = nlp(full_text)

    # TTR
    tokens = [t.text.lower() for t in doc if t.is_alpha]
    vocab = set(tokens)
    ttr = len(vocab) / (len(tokens) + 1e-9)

    # Avg word length
    avg_word_len = statistics.mean([len(t) for t in tokens]) if tokens else 0

    # Heuristic
    word_type = "sophisticated" if avg_word_len > 5.0 else "common"

    # Jargon detection
    jargon_keywords = {"swap", "hedge", "futures", "synergy", "compliance", "litigation", "forex", "collateral"}
    jargon_count = sum(1 for w in tokens if w in jargon_keywords)
    if jargon_count > 10:
        jargon_presence = "high"
    else:
        jargon_presence = "low"

    return {
        "word_type": word_type,
        "lexical_richness_TTR": ttr,
        "jargon_presence": jargon_presence,
        "avg_word_length": avg_word_len
    }

########################################################################
# 3. Structure
########################################################################

def measure_structure(emails):
    """
    Mesure un 'internal_logic' (well_structured vs poorly_structured) 
    via paragraphes et connecteurs.
    """
    connectors = {"therefore", "however", "moreover", "thus", "consequently", "firstly", "secondly", "finally"}
    paragraphs_count = 0
    connectors_count = 0
    total_emails = len(emails)

    for email in emails:
        paragraphs_count += email.count("\n\n") + 1
        words = email.lower().split()
        connectors_count += sum(1 for w in words if w in connectors)

    avg_paragraphs = paragraphs_count / (total_emails + 1e-9)
    avg_connectors = connectors_count / (total_emails + 1e-9)

    if avg_paragraphs > 2 and avg_connectors > 1:
        internal_logic = "well_structured"
    else:
        internal_logic = "poorly_structured"

    return {
        "internal_logic": internal_logic,
        "avg_paragraph_segments": avg_paragraphs,
        "avg_logical_connectors": avg_connectors
    }

########################################################################
# 4. Syntax
########################################################################

def measure_syntax(emails):
    """
    - complexity: 'complex' or 'simple' (dépend du ratio de sub clauses)
    - std_sentence_length
    """
    sentence_lens = []
    sub_clause_count = 0
    total_phrases = 0

    for email in emails:
        doc = nlp(email)
        for sent in doc.sents:
            tokens = [t for t in sent if not t.is_space]
            sentence_lens.append(len(tokens))
            total_phrases += 1
            sub_clause_count += sum(1 for t in sent if t.dep_ == "mark")

    ratio_sub = sub_clause_count / (total_phrases + 1e-9)
    complexity = "complex" if ratio_sub > 0.5 else "simple"

    if len(sentence_lens) > 1:
        std_len = statistics.pstdev(sentence_lens)
    else:
        std_len = 0.0

    return {
        "complexity": complexity,
        "std_sentence_length": std_len
    }

########################################################################
# 5. Recurrence of Patterns
########################################################################

def measure_recurrence(emails, top_n=5):
    """
    Frequent 1-grams et 2-grams (ex: top 5).
    """
    all_tokens = []
    for email in emails:
        tokens = [t.text.lower() for t in nlp(email) if t.is_alpha]
        all_tokens.extend(tokens)

    freq_1 = Counter(all_tokens).most_common(top_n)

    all_2grams = []
    for i in range(len(all_tokens) - 1):
        two_gram = (all_tokens[i], all_tokens[i+1])
        all_2grams.append(two_gram)
    freq_2 = Counter(all_2grams).most_common(top_n)

    return {
        "frequent_1grams": freq_1,
        "frequent_2grams": freq_2
    }

########################################################################
# 6. Politeness and Social Conventions
########################################################################

def measure_politeness(emails):
    """
    - closing_formulas_ratio
    - politeness_score (count of 'please', 'thank', etc.)
    """
    closings = {"regards", "sincerely", "best"}
    closing_count = 0
    total_emails = len(emails)

    polite_words = {"please", "thank"}
    polite_count = 0

    for email in emails:
        lower_e = email.lower()
        lines = lower_e.strip().split("\n")
        if lines:
            last_line = lines[-1].strip()
            if any(c in last_line for c in closings):
                closing_count += 1
        
        for w in polite_words:
            polite_count += lower_e.count(w)

    closing_ratio = closing_count / (total_emails + 1e-9)
    politeness_score = polite_count / (total_emails + 1e-9)

    return {
        "closing_formulas_ratio": closing_ratio,
        "politeness_score": politeness_score
    }

########################################################################
# 7. Rhythm and Cadence
########################################################################

def measure_rhythm_cadence(emails):
    """
    - Variation (std) of sentence lengths
    - punctuation_ratio
    """
    all_sentence_lens = []
    punctuation_count = 0
    word_count = 0

    for email in emails:
        doc = nlp(email)
        for sent in doc.sents:
            tokens = [t for t in sent if not t.is_space]
            all_sentence_lens.append(len(tokens))
        punctuation_count += sum(1 for t in email if t in [".", ",", "?", "!", ";", ":"])
        word_count += len(email.split())

    if len(all_sentence_lens) > 1:
        std_len = statistics.pstdev(all_sentence_lens)
    else:
        std_len = 0

    punctuation_ratio = punctuation_count / (word_count + 1e-9)

    return {
        "std_sentence_length_variation": std_len,
        "punctuation_ratio": punctuation_ratio
    }

########################################################################
# Utility Functions
########################################################################

def anonymize_text(text):
    doc = nlp(text)
    new_text = text
    for ent in reversed(doc.ents):
        if ent.label_ in ["PERSON", "ORG"]:
            new_text = new_text[:ent.start_char] + ent.label_ + new_text[ent.end_char:]
    return new_text

def load_enron_emails_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    user_emails = {}
    for user, group in df.groupby("Full_Name"):
        bodies = group["body"].dropna().tolist()
        cleaned_bodies = [b for b in bodies if isinstance(b, str) and b.strip()]
        if cleaned_bodies:
            user_emails[user] = cleaned_bodies
    return user_emails

########################################################################
# 8. Construction du style profile
########################################################################

def build_user_style_profile(user_id, emails):
    """
    Construit le profil stylistique global pour un utilisateur.
    """
    # Anonymisation
    emails = [anonymize_text(e) for e in emails]

    # Ton
    formal_count = 0
    total_emails = len(emails)
    emotion_list = []
    attitude_list = []

    for email in emails:
        form_label = classify_formality_llama(email[:2000])  # Tronque pour éviter de trop longs prompts
        if form_label == "FORMAL":
            formal_count += 1
        emotion_list.append(detect_emotion(email))
        attitude_list.append(detect_attitude(email))

    ratio_formal = formal_count / (total_emails + 1e-9)
    if ratio_formal > 0.7:
        formality_degree = "mostly_formal"
    elif ratio_formal < 0.3:
        formality_degree = "mostly_informal"
    else:
        formality_degree = "mixed"

    from collections import Counter
    emo_counts = Counter(emotion_list)
    if emo_counts:
        main_emotion = emo_counts.most_common(1)[0][0]
    else:
        main_emotion = "neutral"

    att_counts = Counter(attitude_list)
    if att_counts:
        main_attitude = att_counts.most_common(1)[0][0]
    else:
        main_attitude = "assertive"

    tone = {
        "formality_degree": formality_degree,
        "emotional_expression": main_emotion,
        "attitude": main_attitude
    }

    # Autres dimensions
    vocabulary = measure_vocabulary(emails)
    structure = measure_structure(emails)
    syntax = measure_syntax(emails)
    patterns = measure_recurrence(emails, top_n=5)
    politeness = measure_politeness(emails)
    rhythm = measure_rhythm_cadence(emails)

    style_profile = {
        "user_id": user_id,
        "style_profile": {
            "tone": tone,
            "vocabulary": vocabulary,
            "structure": structure,
            "syntax": syntax,
            "recurrence_of_patterns": patterns,
            "politeness_and_social_conventions": politeness,
            "rhythm_and_cadence": rhythm
        }
    }
    return style_profile

def style_profile_to_instructions(style_profile_json):
    """
    Convertit le JSON en un bloc de texte (instructions) à donner au LLM.
    """
    sp = style_profile_json["style_profile"]

    # 1) Tone
    tone_ins = []
    if sp["tone"]["formality_degree"] == "mostly_formal":
        tone_ins.append("Use a formal, professional register without slang.")
    elif sp["tone"]["formality_degree"] == "mostly_informal":
        tone_ins.append("Use a casual, informal register with friendly language.")
    else:
        tone_ins.append("Mix formal and informal language, but mostly stay professional.")

    if sp["tone"]["emotional_expression"] == "emotional":
        tone_ins.append("Inject noticeable emotional words or expressions.")
    else:
        tone_ins.append("Maintain a neutral emotional tone.")
    
    if sp["tone"]["attitude"] == "assertive":
        tone_ins.append("Use direct language, fewer modals, and confident phrasing.")
    else:
        tone_ins.append("Use more modal verbs and hedging for an attenuated approach.")

    # 2) Vocabulary
    vocab = sp["vocabulary"]
    vocab_ins = []
    if vocab["word_type"] == "sophisticated":
        vocab_ins.append("Prefer sophisticated or technical vocabulary if relevant.")
    else:
        vocab_ins.append("Use simpler, common words to maintain clarity.")

    if vocab["lexical_richness_TTR"] > 0.4:
        vocab_ins.append("Maintain a relatively high lexical diversity.")
    else:
        vocab_ins.append("Focus on clarity rather than broad vocabulary.")

    if vocab["jargon_presence"] == "high":
        vocab_ins.append("Include domain-specific jargon (finance, legal, etc.) where appropriate.")
    else:
        vocab_ins.append("Avoid heavy jargon and keep technical terms minimal.")

    # 3) Structure
    structure_ins = []
    if sp["structure"]["internal_logic"] == "well_structured":
        structure_ins.append("Organize the text with clear paragraphs and transitions.")
    else:
        structure_ins.append("Write in a more free-flow manner, fewer explicit transitions.")
    structure_ins.append("Use connectives or transitions as needed for clarity.")

    # 4) Syntax
    syntax_ins = []
    if sp["syntax"]["complexity"] == "complex":
        syntax_ins.append("Use complex sentences with subordinate clauses.")
    else:
        syntax_ins.append("Favor simpler sentences with minimal subordination.")

    # 5) Recurrence
    patterns = sp["recurrence_of_patterns"]
    patterns_ins = []
    freq_1grams = patterns.get("frequent_1grams", [])
    if freq_1grams:
        top_1gram = freq_1grams[0][0]
        patterns_ins.append(f"Try to incorporate the frequent word '{top_1gram}' if it fits.")
    else:
        patterns_ins.append("No specific frequent words to highlight.")

    # 6) Politeness
    pol = sp["politeness_and_social_conventions"]
    pol_ins = []
    if pol["politeness_score"] > 2.0:
        pol_ins.append("Use polite expressions frequently (e.g. 'please', 'thank you').")
    else:
        pol_ins.append("Use polite expressions sparingly.")
    if pol["closing_formulas_ratio"] > 0.2:
        pol_ins.append("End messages with a polite closing (e.g. 'Regards', 'Sincerely').")
    else:
        pol_ins.append("Minimal or no formal closing is needed.")

    # 7) Rhythm & Cadence
    rhythm = sp["rhythm_and_cadence"]
    rhythm_ins = []
    if rhythm["std_sentence_length_variation"] > 5:
        rhythm_ins.append("Vary sentence lengths to create a dynamic flow.")
    else:
        rhythm_ins.append("Keep sentences somewhat uniform in length.")
    if rhythm["punctuation_ratio"] > 0.05:
        rhythm_ins.append("Use punctuation (commas, dashes) liberally to break ideas.")
    else:
        rhythm_ins.append("Use minimal punctuation for a smooth flow.")

    # Combine
    lines = []
    lines.append("### Tone")
    lines.extend(tone_ins)
    lines.append("\n### Vocabulary")
    lines.extend(vocab_ins)
    lines.append("\n### Structure")
    lines.extend(structure_ins)
    lines.append("\n### Syntax")
    lines.extend(syntax_ins)
    lines.append("\n### Recurrence of Patterns")
    lines.extend(patterns_ins)
    lines.append("\n### Politeness & Social Conventions")
    lines.extend(pol_ins)
    lines.append("\n### Rhythm & Cadence")
    lines.extend(rhythm_ins)

    return "\n".join(lines)


def style_juridique():
    pass
