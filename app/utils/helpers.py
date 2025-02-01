import streamlit as st
from pathlib import Path
import base64
import re
import logging

def get_asset_path(asset_type, filename):
    """Fonction utilitaire améliorée pour obtenir les chemins des assets."""
    try:
        path = Path(__file__).parent.parent / "assets" / asset_type / filename
        if not path.exists():
            logging.warning(f"Asset non trouvé: {path}")
            return None
        return path
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du chemin: {e}")
        return None

def load_binary_file(filepath):
    """Charge un fichier binaire et retourne son contenu encodé en base64."""
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier {filepath}: {e}")
        return None

def setup_page_config():
    """Configuration améliorée de la page."""
    try:
        st.markdown("""
            <style>
                /* Masquer uniquement la navigation native de Streamlit */
                section[data-testid="stSidebarNav"] > div:first-child {display: none !important;}
                div.st-emotion-cache-79elbk {display: none !important;}
                
                /* Conserver les autres éléments de l'interface */
                #MainMenu {visibility: hidden;}
                header {visibility: hidden;}
                footer {visibility: hidden;}
            </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        logging.error(f"Erreur de configuration de la page: {e}")

def generate_fake_data():
    """Génère des données factices plus réalistes pour les tuiles."""
    import random
    
    titles = [
        "Indicateur",
        "Métrique",
        "Statistique",
        "Analyse"
    ]
    
    subtitles = [
        "Valeur mesurée",
        "Donnée analysée",
        "Résultat calculé",
        "Score obtenu"
    ]
    
    return [
        {
            "value": random.randint(0, 100),
            "title": f"{random.choice(titles)} {i+1}",
            "subtitle": random.choice(subtitles),
            "trend": random.choice(["↑", "↓", "→"]),
            "change": random.randint(-20, 20)
        } for i in range(16)
    ]

def load_svg_icon(icon_name):
    """Charge et prépare une icône SVG pour l'affichage dans Streamlit."""
    icon_path = get_asset_path("icons", f"{icon_name}.svg")
    if (icon_path.exists()):
        return icon_path.read_text(encoding='utf-8')
    return ""

def apply_custom_css():
    setup_page_config()  # Appeler setup_page_config au début
    try:
        # Chargement de la police
        font_path = get_asset_path("fonts", "Sofia Pro Regular Az.otf")
        font_b64 = load_binary_file(font_path)
        if font_b64:
            st.markdown(
                f"""
                <style>
                @font-face {{
                    font-family: 'Sofia Pro';
                    src: url(data:font/opentype;charset=utf-8;base64,{font_b64}) format('opentype');
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
        
        # Chargement du CSS
        css_path = get_asset_path("", "styles.css")  # Correction ici
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erreur lors du chargement du CSS: {e}")

def add_logo_and_icons():
    """Ajoute le logo et les boutons de navigation sans HTML inline."""
    logo_path = get_asset_path("logo", "Logo_white.png")
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=100)

    st.sidebar.markdown("### Navigation")
    pages = {
        "Home": ("1_Home", "home"),
        "Dashboard": ("pages.2_Dashboard", "circle-nodes"),  # Modifié
        "Chatbot": ("pages.3_Chatbot", "apps")  # Modifié
    }

    for label, (page_script, icon_name) in pages.items():
        col_icon, col_button = st.sidebar.columns([1, 4])
        with col_icon:
            icon_path = get_asset_path("icons", f"{icon_name}.svg")
            if icon_path.exists():
                icon_b64 = load_binary_file(icon_path)
                if icon_b64:
                    st.markdown(
                        "<div style='display:flex; align-items:center; justify-content:center; height:40px;'>",
                        unsafe_allow_html=True
                    )
                    st.image(f"data:image/svg+xml;base64,{icon_b64}", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

        with col_button:
            st.markdown(
                "<div style='display:flex; align-items:center; height:40px;'>",
                unsafe_allow_html=True
            )
            if st.button(label, key=f"nav_{page_script}"):
                script_path = f"{page_script.replace('.', '/')}.py"
                st.switch_page(script_path)
            st.markdown("</div>", unsafe_allow_html=True)

def manage_graph_history(graph_data, max_history=10):
    """Gère l'historique des graphiques avec une limite"""
    if 'graph_history' not in st.session_state:
        st.session_state.graph_history = []
    
    st.session_state.graph_history.append(graph_data)
    
    # Garder uniquement les derniers graphiques
    if len(st.session_state.graph_history) > max_history:
        st.session_state.graph_history = st.session_state.graph_history[-max_history:]

def format_number(number):
    """Formate les grands nombres pour l'affichage"""
    if number >= 1_000_000:
        return f"{number/1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number/1_000:.1f}k"
    return str(number)

def calculate_trend(current, previous):
    """Calcule la tendance et le pourcentage de changement"""
    if previous == 0:
        return "→", 0
    change = ((current - previous) / previous) * 100
    trend = "↑" if change > 0 else "↓" if change < 0 else "→"
    return trend, round(change, 1)

def save_user_preferences(preferences):
    """Sauvegarde les préférences utilisateur"""
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {}
    st.session_state.user_preferences.update(preferences)