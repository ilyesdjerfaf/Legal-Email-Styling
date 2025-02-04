import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from pyvis.network import Network
import pandas as pd
import os
import numpy as np
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# --- Additional imports for GraphRAG ---
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.generation import GraphRAG

# Set page configuration
st.set_page_config(
    page_title="Knowledge Graph",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS and add logos/icons (if available)
from utils.helpers import apply_custom_css, add_logo_and_icons
apply_custom_css()
add_logo_and_icons()

# Page title
st.markdown("""
    <h1 style='margin-bottom: 2rem;'>Knowledge Graph</h1>
""", unsafe_allow_html=True)
st.write("Select one of the queries below to visualize the corresponding subgraph from the database, or ask a question using GraphRAG.")

# --- Connect to the Neo4j database ---
uri = "bolt://localhost:7687"
user = "neo4j"
password = "azzoneo4j"
driver = GraphDatabase.driver(uri, auth=(user, password))

# --- Initialize the GraphRAG components ---
# Define the name of your vector index (this must already exist in your Neo4j instance)
INDEX_NAME = "vector-index-actors"

# Create an embedder (using OpenAI embeddings)
embedder = OpenAIEmbeddings(model="text-embedding-3-large")

# Initialize the vector retriever (this will query your vector index)
retriever = VectorRetriever(driver, INDEX_NAME, embedder)

# Instantiate the LLM; adjust model_name and parameters as needed.
llm = OpenAILLM(model_name="gpt-4o-mini", model_params={"temperature": 0})

# Instantiate the GraphRAG pipeline
rag = GraphRAG(retriever=retriever, llm=llm)

# --- Initialize the embedder and LLM ---
embedder = OpenAIEmbeddings(model="text-embedding-3-large")
llm = OpenAILLM(model_name="gpt-4o-mini", model_params={"temperature": 0})

# --- Load CSV file and compute embeddings ---
@st.cache_data
def load_csv_and_compute_embeddings(csv_path: str):
    """
    Loads the CSV file and computes an embedding for each row's "content" column.
    Returns the DataFrame and a NumPy array of embeddings.
    """
    df = pd.read_csv(csv_path)
    # Ensure the CSV has a column named "content"
    texts = df["n"].tolist()
    # Compute embeddings for each text (this may take some time for large CSVs)
    embeddings = [embedder.embed_query(text) for text in texts]
    return df, np.array(embeddings)

csv_path = "src/knowledge-graph/export.csv"  # Ensure this CSV file exists in your working directory
df, embeddings = load_csv_and_compute_embeddings(csv_path)


def build_graph_from_path_records(records):
    """
    For queries returning a path p (for HAS_ACTION, HAS_INTENTION, PART_OF, etc.),
    extract nodes and relationships.
    """
    nodes = {}
    edges = []
    for record in records:
        path = record["p"]
        # Add all nodes from the path.
        for node in path.nodes:
            nodes[node.id] = node
        # Add all relationships from the path.
        for rel in path.relationships:
            edges.append((rel.start_node.id, rel.end_node.id, dict(rel)))
    return nodes, edges

# --- Helper Functions for Graph Visualization ---
def run_query(query):
    """Executes a given Cypher query and returns the results as a list."""
    with driver.session() as session:
        result = session.run(query)
        return list(result)


def build_graph_from_email_actor(records):
    """
    For queries that return email, actor, and pubact,
    add each as a node and create edges between them.
    """
    nodes = {}
    edges = []
    for record in records:
        email = record["email"]
        actor = record["actor"]
        pubact = record["pubact"]
        # Add nodes; use their Neo4j id as key.
        nodes[email.id] = email
        nodes[actor.id] = actor
        nodes[pubact.id] = pubact
        # Create edges from the email to both actor and public act.
        edges.append((email.id, actor.id, {}))
        edges.append((email.id, pubact.id, {}))
    return nodes, edges

def show_graph(nodes, edges, height=750, width=1000):
    """
    Build a Pyvis network graph from nodes and edges, save as HTML,
    and embed it into the Streamlit app.
    """
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    
    # Add nodes with a label and a tooltip (title) showing all properties.
    for node_id, node in nodes.items():
        props = dict(node)
        if props.get('label') == 'Email':
            # make a yellow colour for the Email
            label = props.get("name", f"Email {node_id}")
            net.add_node(node_id, label=label, title=str(props), color='#97c2fc')
        if props.get('label') == 'Acteur':
            label = props.get("name", f"Acteur {node_id}")
            net.add_node(node_id, label=label, title=str(props), color='#772ccf')
        if props.get('label') == 'PublicAct':
            label = props.get("name", f"PublicAct {node_id}")
            net.add_node(node_id, label=label, title=str(props), color='#772ccc')
        else:
            label = props.get("name", f"{props.get('label')} {node_id}")
            net.add_node(node_id, label=label, title=str(props), color='#ffffff')


    
    # Add edges.
    for source, target, _ in edges:
        net.add_edge(source, target)
    
    # Save and embed the graph HTML.
    graph_path = "graph.html"
    net.save_graph(graph_path)
    with open(graph_path, "r", encoding="utf-8") as html_file:
        graph_html = html_file.read()
    components.html(graph_html, height=height, width=width)

# --- Predefined Query Buttons ---
if st.button("Show HAS_ACTION relationships"):
    query = "MATCH p=()-[r:HAS_ACTION]->() RETURN p LIMIT 25"
    records = run_query(query)
    if records:
        nodes, edges = build_graph_from_path_records(records)
        show_graph(nodes, edges)
    else:
        st.info("No HAS_ACTION relationships found.")

if st.button("Show HAS_INTENTION relationships"):
    query = "MATCH p=()-[r:HAS_INTENTION]->() RETURN p LIMIT 25"
    records = run_query(query)
    if records:
        nodes, edges = build_graph_from_path_records(records)
        show_graph(nodes, edges)
    else:
        st.info("No HAS_INTENTION relationships found.")

if st.button("Show PART_OF relationships"):
    query = "MATCH p=()-[r:PART_OF]->() RETURN p LIMIT 25"
    records = run_query(query)
    if records:
        nodes, edges = build_graph_from_path_records(records)
        show_graph(nodes, edges)
    else:
        st.info("No PART_OF relationships found.")

if st.button("Show Email, Actor, and PublicAct relationships"):
    query = (
        "MATCH (pubact:PublicAct)<-[:HAS_ACTION|HAS_INTENTION]-(email:Email)"
        "-[:MENTIONS|SENT_BY|RECEIVED_BY]->(actor:Acteur) "
        "RETURN email, actor, pubact LIMIT 25"
    )
    records = run_query(query)
    if records:
        nodes, edges = build_graph_from_email_actor(records)
        show_graph(nodes, edges)
    else:
        st.info("No Email, Actor, and PublicAct relationships found.")

# --- GraphRAG: Ask a Question Section ---
st.markdown("### Ask a Question using GraphRAG")
user_question = st.text_input("Enter your question about the knowledge graph:")

if st.button("Submit Question"):
    if user_question:
        with st.spinner("Querying GraphRAG..."):
            try:
                # Use GraphRAG to search the graph using the natural language question.
                # The retriever_config can be adjusted (e.g. top_k for number of results)
                response = rag.search(query_text=user_question, retriever_config={"top_k": 5})
                print("Response:",response)
                st.markdown("#### GraphRAG Answer")
                st.write(response.answer)
            except Exception as e:
                st.error(f"Error during GraphRAG search: {e}")
    else:
        st.warning("Please enter a question.")

driver.close()
