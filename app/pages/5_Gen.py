import streamlit as st

# Configuration de la page DOIT être le premier appel à Streamlit
st.set_page_config(
    page_title="Email Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path
import importlib.util
from datetime import datetime
import json
import pickle

# Import direct depuis src/generation/utils.py
generation_path = Path(__file__).parent.parent.parent / "src" / "generation" / "utils.py"
spec = importlib.util.spec_from_file_location("generation_utils", generation_path)
generation_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generation_utils)

from utils.helpers import apply_custom_css, add_logo_and_icons

# Utiliser les fonctions importées depuis generation_utils uniquement
load_enron_emails_from_csv = generation_utils.load_enron_emails_from_csv
build_user_style_profile = generation_utils.build_user_style_profile
style_profile_to_instructions = generation_utils.style_profile_to_instructions
llm = generation_utils.llm
style_juridique = generation_utils.style_juridique
get_user_descriptions_by_date = generation_utils.get_user_descriptions_by_date

# Charger les données avant la mise en page
# Correction des chemins pour pointer vers src/generation
data_path = Path(__file__).parent.parent.parent / "src" / "generation"
CSV_PATH = str(data_path / "sample_graph.csv")
link_events = str(data_path / "extracted_facts.json")
users_path = str(data_path / "sample_users_graph.pkl")

# Après la définition des chemins, ajoutez le chargement des données
try:
    with open(link_events, 'r', encoding='utf-8') as f:
        links = json.load(f)
except FileNotFoundError:
    st.error(f"File not found: {link_events}")
    links = {}
except json.JSONDecodeError:
    st.error(f"Invalid JSON file: {link_events}")
    links = {}
except Exception as e:
    st.error(f"Error loading file {link_events}: {str(e)}")
    links = {}

@st.cache_data
def load_data(csv_path):
    try:
        return load_enron_emails_from_csv(csv_path)
    except Exception as e:
        st.error(f"Error loading CSV data: {str(e)}")
        return {}

# Charger les données avant l'interface utilisateur
user_emails_map = load_data(CSV_PATH)
all_users = sorted(list(user_emails_map.keys()))

# Configuration de la page et styles
apply_custom_css()
add_logo_and_icons()

# Funnel state management
if "funnel_state" not in st.session_state:
    st.session_state.funnel_state = {
        "profile_generated": False,  # Combine user_selected et profile_generated
        "facts_generated": False,
        "email_generated": False
    }

# Initialisation du session state
if "style_profile" not in st.session_state:
    st.session_state["style_profile"] = None
if "style_instructions" not in st.session_state:
    st.session_state["style_instructions"] = None
if "facts" not in st.session_state:
    st.session_state["facts"] = None
if "generated_email" not in st.session_state:
    st.session_state["generated_email"] = None
if "generated_email_legal" not in st.session_state:
    st.session_state["generated_email_legal"] = None
if "generation_in_progress" not in st.session_state:
    st.session_state["generation_in_progress"] = False
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "single"  # or "compare"

# Main UI container
with st.container():
    # Header with progress indicator
    st.markdown("""
        <div style='background: linear-gradient(90deg, #353863 0%, #2A2D4C 100%); 
                    padding: 2rem; 
                    border-radius: 15px; 
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>
            <h1 style='margin-bottom: 0.5rem;'>Email Generator</h1>
            <p style='color: #B0B0B0; font-size: 1.1rem;'>Follow the steps below to generate your customized email</p>
        </div>
    """, unsafe_allow_html=True)

    # Funnel Steps - Fixed size boxes
    steps_col1, steps_col2, steps_col3 = st.columns(3)
    
    step_infos = [
        (steps_col1, "Select & Generate Profile", "profile_generated", 1),
        (steps_col2, "Generate Facts", "facts_generated", 2),
        (steps_col3, "Generate Email", "email_generated", 3)
    ]
    
    # Custom CSS for fixed size boxes
    st.markdown("""
        <style>
            [data-testid="column"] {
                width: calc(33.33% - 1rem) !important;
                min-width: 250px !important;
            }
            
            .step-box {
                min-height: 120px !important;
                height: 120px !important;
                width: 100% !important;
                box-sizing: border-box !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    for col, step_name, step_key, step_num in step_infos:
        is_completed = st.session_state.funnel_state[step_key]
        is_active = (
            step_num == 1 or 
            (step_num > 1 and st.session_state.funnel_state[list(st.session_state.funnel_state.keys())[step_num-2]])
        )
        
        with col:
            st.markdown(f"""
                <div class="step-box" style="
                    background-color: {'#4CAF50' if is_completed else '#353863'};
                    opacity: {1 if is_active else 0.5};
                    padding: 1.5rem;
                    border-radius: 10px;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;">
                    <h4 style="margin: 0;">{step_num}. {step_name}</h4>
                    <p style="color: #B0B0B0; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
                        {"✓ Completed" if is_completed else "Waiting..."}
                    </p>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content area
    with st.container():
        # Step 1: User Selection & Profile Generation (Combined)
        with st.expander("Step 1: Select & Generate Profile", expanded=not st.session_state.funnel_state["profile_generated"]):
            st.markdown("""
                <div style='background-color: #2A2D4C; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;'>
                    <p style='color: #B0B0B0;'>Select a user and generate their style profile.</p>
                </div>
            """, unsafe_allow_html=True)
            
            selected_user = st.selectbox("Select User Profile", all_users, key="user_select")
            if st.button("🎯 Generate Profile", use_container_width=True):
                with st.spinner("Generating profile..."):
                    emails = user_emails_map[selected_user]
                    style_profile = build_user_style_profile(selected_user, emails)
                    instructions = style_profile_to_instructions(style_profile)
                    
                    st.session_state["selected_user"] = selected_user
                    st.session_state["style_profile"] = style_profile
                    st.session_state["style_instructions"] = instructions
                    st.session_state.funnel_state["profile_generated"] = True
                    st.rerun()

            if st.session_state.get("style_profile"):
                st.json(st.session_state["style_profile"])

        # Step 2: Generate Facts
        if st.session_state.funnel_state["profile_generated"]:
            with st.expander("Step 2: Generate Facts", expanded=not st.session_state.funnel_state["facts_generated"]):
                st.markdown("""
                    <div style='background-color: #2A2D4C; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;'>
                        <p style='color: #B0B0B0;'>Generate relevant facts about the user for email content.</p>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("📋 Generate Facts", use_container_width=True):
                    with st.spinner("Generating facts..."):
                        try:
                            facts = get_user_descriptions_by_date(links, st.session_state["selected_user"])
                            if not facts:
                                facts = "No facts available for this user."
                            st.session_state["facts"] = facts
                            st.session_state.funnel_state["facts_generated"] = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error generating facts: {str(e)}")

                if st.session_state.get("facts"):
                    st.markdown(f"""
                        <div style='background-color: #353863; padding: 1rem; border-radius: 8px;'>
                            <pre style='color: #E0E0E0;'>{st.session_state["facts"]}</pre>
                        </div>
                    """, unsafe_allow_html=True)

        # Step 3: Generate Email
        if st.session_state.funnel_state["facts_generated"]:
            with st.expander("Step 3: Generate Email", expanded=True):
                st.markdown("""
                    <div style='background-color: #2A2D4C; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;'>
                        <p style='color: #B0B0B0;'>Generate and compare different email styles.</p>
                    </div>
                """, unsafe_allow_html=True)

                # Add view toggle and auto-generation for compare mode
                view_col1, view_col2 = st.columns([3, 1])
                with view_col2:
                    # Modify view toggle handling to update completed state
                    previous_mode = st.session_state.get("view_mode", "single")
                    view_mode = st.radio(
                        "View Mode",
                        ["Single", "Compare"],
                        key="view_mode_radio",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    
                    # Update email_generated state when switching to compare
                    if view_mode.lower() == "compare" and previous_mode != "compare":
                        # Si au moins un email existe déjà, marquer comme complété
                        if st.session_state.get("generated_email") or st.session_state.get("generated_email_legal"):
                            st.session_state.funnel_state["email_generated"] = True
                        else:
                            # Generate both emails only if they don't exist
                            with st.spinner('Generating both email styles...'):
                                # Generate user-style email
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

                                # Generate legal-style email
                                inst = style_juridique()
                                system_prompt_legal = f"""
                                You are an AI assistant specialized in drafting legal emails.

                                Below are the defining characteristics of a proper legal-style email:
                                {inst}

                                Constraints:
                                1. Carefully follow the listed characteristics for a legal email.
                                2. Use the facts provided below to shape the content of the email.
                                3. Write the email in English, in a formal and professional tone.
                                """

                                user_prompt_legal = f"""
                                Here are the facts to include in the legal email:

                                {st.session_state["facts"]}
                                """

                                response_legal = llm.invoke([
                                    ("system", system_prompt_legal),
                                    ("human", user_prompt_legal)
                                ])
                                st.session_state["generated_email_legal"] = response_legal.content
                            st.session_state.funnel_state["email_generated"] = True
                        st.rerun()
                    
                    st.session_state["view_mode"] = view_mode.lower()

                # Generation buttons (only show in single mode)
                if st.session_state["view_mode"] == "single":
                    email_col1, email_col2 = st.columns(2)
                    with email_col1:
                        if st.button("✉️ Generate User-Style Email", use_container_width=True):
                            st.session_state.funnel_state["email_generated"] = True
                            st.session_state["generated_email_legal"] = None  # Clear other generation
            
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

                            with st.spinner('Generating user-style email...'):
                                response = llm.invoke([
                                    ("system", system_prompt),
                                    ("human", user_prompt)
                                ])
                                st.session_state["generated_email"] = response.content
                            
                            st.session_state["generation_in_progress"] = False
                
                    with email_col2:
                        if st.button("⚖️ Generate Legal Email", use_container_width=True):
                            st.session_state.funnel_state["email_generated"] = True
                            st.session_state["generated_email"] = None  # Clear other generation
            
                            inst = style_juridique()
                            system_prompt_legal = f"""
                            You are an AI assistant specialized in drafting legal emails.

                            Below are the defining characteristics of a proper legal-style email:
                            {inst}

                            Constraints:
                            1. Carefully follow the listed characteristics for a legal email.
                            2. Use the facts provided below to shape the content of the email.
                            3. Write the email in English, in a formal and professional tone.
                            """

                            user_prompt_legal = f"""
                            Here are the facts to include in the legal email:

                            {st.session_state["facts"]}
                            """

                            with st.spinner('Generating legal email...'):
                                response_legal = llm.invoke([
                                    ("system", system_prompt_legal),
                                    ("human", user_prompt_legal)
                                ])
                                st.session_state["generated_email_legal"] = response_legal.content
                            
                            st.session_state["generation_in_progress"] = False

                # Display emails based on view mode
                if st.session_state.get("generated_email") or st.session_state.get("generated_email_legal"):
                    if st.session_state["view_mode"] == "compare":
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("""
                                <div style='background-color: #353863; padding: 1.5rem; border-radius: 10px; height: 100%;'>
                                    <h4 style='color: #FF5F5F; margin-bottom: 1rem;'>User-Style Email</h4>
                                    <div style='background-color: #2A2D4C; padding: 1rem; border-radius: 8px;'>
                            """, unsafe_allow_html=True)
                            if st.session_state.get("generated_email"):
                                st.write(st.session_state["generated_email"])
                            else:
                                st.info("No user-style email generated yet")
                            st.markdown("</div></div>", unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown("""
                                <div style='background-color: #353863; padding: 1.5rem; border-radius: 10px; height: 100%;'>
                                    <h4 style='color: #FF5F5F; margin-bottom: 1rem;'>Legal-Style Email</h4>
                                    <div style='background-color: #2A2D4C; padding: 1rem; border-radius: 8px;'>
                            """, unsafe_allow_html=True)
                            if st.session_state.get("generated_email_legal"):
                                st.write(st.session_state["generated_email_legal"])
                            else:
                                st.info("No legal-style email generated yet")
                            st.markdown("</div></div>", unsafe_allow_html=True)
                    else:
                        # Original single view display code
                        if st.session_state.get("generated_email"):
                            st.markdown("""
                                <div style='background-color: #353863; padding: 1.5rem; border-radius: 10px; margin-top: 1rem;'>
                                    <h4 style='color: #FF5F5F; margin-bottom: 1rem;'>Generated User-Style Email</h4>
                                    <div style='background-color: #2A2D4C; padding: 1rem; border-radius: 8px;'>
                            """, unsafe_allow_html=True)
                            st.write(st.session_state["generated_email"])
                            st.markdown("</div></div>", unsafe_allow_html=True)

                        if st.session_state.get("generated_email_legal"):
                            st.markdown("""
                                <div style='background-color: #353863; padding: 1.5rem; border-radius: 10px; margin-top: 1rem;'>
                                    <h4 style='color: #FF5F5F; margin-bottom: 1rem;'>Generated Legal Email</h4>
                                    <div style='background-color: #2A2D4C; padding: 1rem; border-radius: 8px;'>
                            """, unsafe_allow_html=True)
                            st.write(st.session_state["generated_email_legal"])
                            st.markdown("</div></div>", unsafe_allow_html=True)

# Add reset button at the bottom
if any(st.session_state.funnel_state.values()):
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reset All", use_container_width=True):
        for key in st.session_state.funnel_state:
            st.session_state.funnel_state[key] = False
        st.session_state["style_profile"] = None
        st.session_state["style_instructions"] = None
        st.session_state["facts"] = None
        st.session_state["generated_email"] = None
        st.session_state["generated_email_legal"] = None
        st.rerun()

# Styles supplémentaires
st.markdown("""
    <style>
        /* Style des conteneurs */
        div[data-testid="stSelectbox"] {
            background-color: #353863;
            border-radius: 8px;
            padding: 0.5rem;
            margin-bottom: 1rem;
        }
        
        /* Style des boutons */
        .stButton > button {
            background-color: #353863 !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            padding: 0.75rem 1rem !important;
            font-size: 1rem !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            background-color: #FF5F5F !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        /* Style des conteneurs JSON */
        .element-container div[class*="stJson"] {
            background-color: #353863 !important;
            border-radius: 8px;
            padding: 1rem;
        }
    </style>
""", unsafe_allow_html=True)
