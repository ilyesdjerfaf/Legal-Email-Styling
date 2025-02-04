import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from pyvis.network import Network
import os

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
st.write("Select one of the queries below to visualize the corresponding subgraph from the database.")

# Connect to the Neo4j database
uri = "bolt://localhost:7687"
user = "neo4j"
password = "azzoneo4j"
driver = GraphDatabase.driver(uri, auth=(user, password))

def run_query(query):
    """Executes a given Cypher query and returns the results as a list."""
    with driver.session() as session:
        result = session.run(query)
        return list(result)

def build_graph_from_path_records(records):
    """
    For queries returning a path p (for HAS_ACTION, HAS_INTENTION, PART_OF),
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

def build_graph_from_email_actor(records):
    """
    For the query that returns email, actor, pubact,
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
    # Create a Pyvis network.
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    
    # Add nodes with a label and a tooltip (title) showing all properties.
    for node_id, node in nodes.items():
        # Convert node to a dictionary to access its properties.
        props = dict(node)
        # Use the 'name' property if it exists; otherwise, use a default label.
        label = props.get("name", f"Node {node_id}")
        # Set the title attribute to show all properties on hover.
        net.add_node(node_id, label=label, title=str(props))
    
    # Add edges.
    for source, target, _ in edges:
        net.add_edge(source, target)
    
    # Save the graph to an HTML file.
    graph_path = "graph.html"
    net.save_graph(graph_path)
    
    # Read and embed the HTML visualization.
    with open(graph_path, "r", encoding="utf-8") as html_file:
        graph_html = html_file.read()
    components.html(graph_html, height=height, width=width)

# --- Query Buttons ---
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
        "RETURN email, actor, pubact"
    )
    records = run_query(query)
    if records:
        nodes, edges = build_graph_from_email_actor(records)
        show_graph(nodes, edges)
    else:
        st.info("No Email, Actor, and PublicAct relationships found.")

driver.close()
