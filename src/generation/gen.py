import streamlit as st
import pandas as pd
import json
import pickle
from datetime import datetime
from utils import (
    load_enron_emails_from_csv,
    build_user_style_profile,
    style_profile_to_instructions,
    llm
)

#####################################
# 1) Chargement des données
#####################################
CSV_PATH = "sample_graph.csv"
link_events = "extracted_facts.json"
users_path = "sample_users_graph.pkl"

with open(link_events) as f:
    links = json.load(f)

with open(users_path, 'rb') as f:
    users = pickle.load(f)

#####################################
# 2) Functions to get user descriptions
#####################################
@st.cache_data
def get_user_descriptions_by_date(json_data, user_email):
    """
    Fetches the descriptions of facts for a given user, sorted by date (oldest to newest).

    Args:
        json_data (dict): JSON object containing user event information.
        user_email (str): The email of the user to fetch the descriptions for.

    Returns:
        str: A formatted string of descriptions sorted by date.
    """
    if user_email not in json_data:
        return "No facts available for this user."
    events = json_data[user_email]

    sorted_events = sorted(
        events,
        key=lambda event: datetime.fromisoformat(event['date'])
    )

    ev = [event['description'] for event in sorted_events]

    return "\n".join([f"* {i+1}. {event}" for i, event in enumerate(ev)])

@st.cache_data
def load_data(csv_path):
    return load_enron_emails_from_csv(csv_path)

user_emails_map = load_data(CSV_PATH)

#####################################
# 3) Configuration Streamlit
#####################################
st.title("Application de génération d'e-mails selon le style d'utilisateur")

# Initialisation de l'état
if "style_profile" not in st.session_state:
    st.session_state["style_profile"] = None

if "style_instructions" not in st.session_state:
    st.session_state["style_instructions"] = None

if "facts" not in st.session_state:
    st.session_state["facts"] = None

if "generated_email" not in st.session_state:
    st.session_state["generated_email"] = None

#####################################
# 4) Sélection de l'utilisateur
#####################################
all_users = sorted(list(user_emails_map.keys()))
selected_user = st.selectbox("Sélectionnez un utilisateur :", all_users)

#####################################
# 5) Bouton : Générer la carte ID
#####################################
if st.button("Générer la carte ID"):
    emails = user_emails_map[selected_user]
    style_profile = build_user_style_profile(selected_user, emails)
    instructions = style_profile_to_instructions(style_profile)

    # Sauvegarde dans la session
    st.session_state["style_profile"] = style_profile
    st.session_state["style_instructions"] = instructions
    st.session_state["facts"] = None
    st.session_state["generated_email"] = None

# Affichage de la carte ID
if st.session_state["style_profile"] is not None:
    st.subheader("Carte d'identité stylistique (JSON)")
    st.json(st.session_state["style_profile"])

#####################################
# 6) Bouton : Générer la base des faits
#####################################
if st.session_state["style_profile"] is not None:
    if st.button("Générer la base des faits"):
        facts = get_user_descriptions_by_date(links, selected_user)
        st.session_state["facts"] = facts

# Affichage des faits
if st.session_state["facts"] is not None:
    st.subheader("Base des faits (générée)")
    st.text(st.session_state["facts"])

#####################################
# 7) Bouton : Générer l'e-mail
#####################################
if st.session_state["facts"] is not None and st.session_state["style_instructions"] is not None:
    if st.button("Générer l'e-mail"):
        system_prompt = f"""
        You are a professional AI writing assistant.
        You will receive some style instructions and some facts.
        Your task is to produce an email in the style described by the instructions.

        Style Instructions:
        {st.session_state["style_instructions"]}

        Constraints:
        1. Follow the style instructions carefully.
        2. Use the facts provided to shape the content of the email.
        3. Write in English.
        """

        user_prompt = f"""
        Please write an email using the following facts:

        {st.session_state["facts"]}
        """

        response = llm.invoke([
            ("system", system_prompt),
            ("human", user_prompt)
        ])

        st.session_state["generated_email"] = response.content

# Affichage de l'e-mail généré
if st.session_state["generated_email"] is not None:
    st.subheader("E-mail généré")
    st.write(st.session_state["generated_email"])
