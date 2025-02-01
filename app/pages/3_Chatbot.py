import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from utils.helpers import apply_custom_css, add_logo_and_icons

st.set_page_config(
    page_title="Chatbot",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_css()
add_logo_and_icons()

# Titre de la page
st.title("ChatBot")

# Initialisation améliorée de l'état du chat
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

def process_message(message):
    """Traite et valide le message avant envoi"""
    return message.strip() if message else None

# Zone de chat
with st.container():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Votre message:")
    if user_input:
        processed_input = process_message(user_input)
        if processed_input:
            st.session_state.messages.append({"role": "user", "content": processed_input})
            # Simulation de réponse (à remplacer par votre logique)
            response = f"Réponse à: {processed_input}"
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()  # Remplacement de experimental_rerun() par rerun()