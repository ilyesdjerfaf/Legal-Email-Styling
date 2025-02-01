import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import apply_custom_css, add_logo_and_icons

st.set_page_config(
    page_title="Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_css()
add_logo_and_icons()

# Initialisation des états de session
if 'graph_history' not in st.session_state:
    st.session_state.graph_history = []
if 'chart_type' not in st.session_state:
    st.session_state.chart_type = "Barres"

# Titre de la page
st.title("Dashboard")

# Organisation des entrées
col1, col2 = st.columns([1, 3])
with col1:
    chart_type = st.selectbox(
        "Type de graphique",
        ["Barres", "Ligne", "Aires", "Scatter"],
        key="chart_select"
    )
    st.session_state.chart_type = chart_type

# Barre de question sur toute la largeur
question = st.chat_input("Posez une question pour générer un graphique...")

if question:
    df = pd.DataFrame({
        'x': range(10),
        'y': range(10, 20)
    })
    
    # Utilisation du type de graphique stocké
    if st.session_state.chart_type == "Barres":
        fig = px.bar(df, x='x', y='y', title=question)
    elif st.session_state.chart_type == "Ligne":
        fig = px.line(df, x='x', y='y', title=question)
    elif st.session_state.chart_type == "Aires":
        fig = px.area(df, x='x', y='y', title=question)
    else:
        fig = px.scatter(df, x='x', y='y', title=question)

    fig.update_layout(
        plot_bgcolor='rgba(53, 56, 99, 0.1)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    st.plotly_chart(fig, use_container_width=True, key="main_graph")
    
    # Sauvegarder le graphique dans l'historique
    st.session_state.graph_history.append({
        'question': question,
        'timestamp': pd.Timestamp.now(),
        'fig': fig
    })

# Mise à jour du type de graphique dans la session
st.session_state.chart_type = chart_type

# Affichage des graphiques récents
if st.session_state.graph_history:
    st.subheader("Graphiques récents")
    cols = st.columns(2)
    for i, graph in enumerate(reversed(st.session_state.graph_history[-4:])):
        with cols[i % 2]:
            st.caption(f"Question: {graph['question']}")
            st.plotly_chart(graph['fig'], use_container_width=True, key=f"history_graph_{i}")

# Grille de graphiques
cols = st.columns(2)
for i in range(4):
    with cols[i % 2]:
        df = pd.DataFrame({
            'x': range(5),
            'y': range(5, 10)
        })
        fig = px.line(df, x='x', y='y', title=f"Graphique {i+1}")
        fig.update_layout(
            plot_bgcolor='rgba(53, 56, 99, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True, key=f"static_graph_{i}")