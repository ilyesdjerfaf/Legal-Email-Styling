import streamlit as st
import pandas as pd
import json

from utils import (
    load_enron_emails_from_csv,
    build_user_style_profile,
    style_profile_to_instructions,
    llm
)

#####################################
# 1) Chargement des données
#####################################
CSV_PATH = "mails.csv"

@st.cache_data
def load_data(csv_path):
    return load_enron_emails_from_csv(csv_path)

user_emails_map = load_data(CSV_PATH)

#####################################
# 2) Configuration Streamlit
#####################################
st.title("Application de génération d'e-mails selon le style d'utilisateur")

# Initialisation de l'état
if "style_profile" not in st.session_state:
    st.session_state["style_profile"] = None

if "style_instructions" not in st.session_state:
    st.session_state["style_instructions"] = None

if "generated_email" not in st.session_state:
    st.session_state["generated_email"] = None

if "generated_email_legal" not in st.session_state:
    st.session_state["generated_email_legal"] = None

# Nouveau champ pour le texte devant la cour pénale
if "generated_penal_statement" not in st.session_state:
    st.session_state["generated_penal_statement"] = None

# Faits par défaut (modifiable par l'utilisateur)
default_facts = """\
- We need to sign a new trading agreement with Org for the next quarter
- Deadline is next Friday
- We require approval from the finance team
- The cost estimation is 15 million dollars
"""

# Style juridique (EN)
LEGAL_STYLE_INSTRUCTIONS = """
Characteristics of a legal email:

1. The email must contain a clear and concise subject line.
2. Use a professional salutation, such as 'Dear Sir/Madam,' 'Hello Mr. X,' or 'Maître Y' if relevant.
3. Favor a medium-length structure: avoid bullet points, organize content into paragraphs and line breaks.
4. Body: adopt a formal, direct tone; use sophisticated or technical language; optionally cite laws/articles (GREEN FLAG); avoid emotional expressions.
5. Use formal valedictions such as 'Kind regards,' or 'Yours sincerely.'
6. Include a complete signature.
7. Employ abbreviations and acronyms to indicate professionalism (e.g., references to codes, articles, or legal citations).
"""

# Nouveau style : Relater les faits devant une cour pénale (FR)
PENAL_COURT_INSTRUCTIONS = """
Caractéristiques d'un exposé des faits devant une cour pénale :

1. Adoptez un ton formel, respectueux et objectif.
2. Présentez les faits de manière chronologique ou logique, sans omission cruciale.
3. Évitez tout style trop narratif ou émotionnel : il s'agit d'un exposé juridique.
4. Vous pouvez référencer des articles de loi ou dispositions pénales si nécessaire.
5. Pas de salutations ni de formule de politesse de type courrier/email.
6. Le document doit être clair, concis et explicite quant aux faits reprochés ou constatés.
7. Pensez à inclure les informations clés : date, lieu, personnes impliquées, etc., si fournies.
"""

#####################################
# 3) Sélection de l'utilisateur
#####################################
all_users = sorted(list(user_emails_map.keys()))
selected_user = st.selectbox("Sélectionnez un utilisateur :", all_users)

#####################################
# 4) Bouton : Générer la carte ID
#####################################
if st.button("Générer la carte ID"):
    emails = user_emails_map[selected_user]
    style_profile = build_user_style_profile(selected_user, emails)
    instructions = style_profile_to_instructions(style_profile)

    # Sauvegarde dans la session
    st.session_state["style_profile"] = style_profile
    st.session_state["style_instructions"] = instructions
    st.session_state["generated_email"] = None
    st.session_state["generated_email_legal"] = None
    st.session_state["generated_penal_statement"] = None

#####################################
# 5) Affichage de la carte ID & Instructions
#####################################
if st.session_state["style_profile"] is not None:
    st.subheader("Carte d'identité stylistique (JSON)")
    st.json(st.session_state["style_profile"])

if st.session_state["style_instructions"] is not None:
    st.subheader("Instructions de style (texte)")
    st.write(st.session_state["style_instructions"])

#####################################
# 6) Zone de texte : Faits personnalisables
#####################################
facts_input = st.text_area(
    label="Faits à intégrer dans le texte :",
    value=default_facts,
    height=150
)

#####################################
# 7) Boutons de génération
#####################################

col1, col2, col3 = st.columns(3)

# Bouton "Générer l'e-mail" (style profil utilisateur)
with col1:
    if st.session_state["style_instructions"] is not None:
        if st.button("Générer l'e-mail (style utilisateur)"):
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
            
            {facts_input}
            """

            response = llm.invoke([
                ("system", system_prompt),
                ("human", user_prompt)
            ])

            st.session_state["generated_email"] = response.content

# Bouton "Générer l'e-mail juridique" (EN)
with col2:
    if st.session_state["style_instructions"] is not None:
        if st.button("Générer l'e-mail juridique (EN)"):
            system_prompt_legal = f"""
            You are an AI assistant specialized in drafting legal emails.

            Below are the defining characteristics of a proper legal-style email:
            {LEGAL_STYLE_INSTRUCTIONS}

            Constraints:
            1. Carefully follow the listed characteristics for a legal email.
            2. Use the facts provided below to shape the content of the email.
            3. Write the email in English, in a formal and professional tone.
            """

            user_prompt_legal = f"""
            Here are the facts to include in the legal email:

            {facts_input}
            """

            response_legal = llm.invoke([
                ("system", system_prompt_legal),
                ("human", user_prompt_legal)
            ])

            st.session_state["generated_email_legal"] = response_legal.content

# Bouton "Relater les faits devant une cour pénale" (FR)
with col3:
    if st.session_state["style_instructions"] is not None:
        if st.button("Relater faits en cour pénale (FR)"):
            system_prompt_penal = f"""
            Vous êtes un assistant IA spécialisé dans la rédaction d'exposés de faits pour une cour pénale.

            {PENAL_COURT_INSTRUCTIONS}

            Contraintes :
            1. Tenez compte des caractéristiques listées ci-dessus.
            2. Utilisez les faits fournis ci-dessous pour construire l'exposé.
            3. Rédigez en français, de manière formelle et claire.
            """

            user_prompt_penal = f"""
            Voici les faits à présenter devant la cour pénale :

            {facts_input}
            """

            response_penal = llm.invoke([
                ("system", system_prompt_penal),
                ("human", user_prompt_penal)
            ])

            response_english = llm.invoke([
                ("system", "translate in englith the user texte"),
                ("human", response_penal.content)
            ])

            st.session_state["generated_penal_statement"] = response_penal.content

#####################################
# 8) Affichage des résultats 
#####################################
if st.session_state["generated_email"] is not None:
    st.subheader("E-mail généré (selon la carte ID utilisateur)")
    st.write(st.session_state["generated_email"])

if st.session_state["generated_email_legal"] is not None:
    st.subheader("E-mail généré (Style Juridique, EN)")
    st.write(st.session_state["generated_email_legal"])

if st.session_state["generated_penal_statement"] is not None:
    st.subheader("Exposé des faits devant la cour pénale (EN)")
    st.write(st.session_state["generated_penal_statement"])
