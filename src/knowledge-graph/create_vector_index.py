from neo4j import GraphDatabase
from neo4j_graphrag.indexes import create_vector_index, upsert_vector
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
import os
load_dotenv()
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# --- Configuration ---
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "azzoneo4j"  # Update with your actual password
INDEX_NAME = "vector-index"  # Name for your vector index

# --- Connect to Neo4j ---
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# --- Create the Vector Index ---
# This index will be created on nodes with label "Chunk" and will index the "embedding" property.
# The dimensions must match your embedding model (here assumed to be 3072 dimensions).
create_vector_index(
    driver,
    INDEX_NAME,
    label="Chunk",
    embedding_property="embedding",
    dimensions=3072,  # Adjust to your embedding model's output dimensions
    similarity_fn="euclidean",
)
print("Vector index created.")

# --- Initialize the Embedder ---
# Using OpenAI embeddings; ensure your OPENAI_API_KEY is set in your environment.
embedder = OpenAIEmbeddings(model="text-embedding-3-large")

# --- Retrieve Existing Nodes from the Database ---
def get_chunks():
    """
    Retrieve All nodes in the database that have the label "Email"
    """
    query = "MATCH (c:Email) RETURN c"
    with driver.session() as session:
        result = session.run(query)
        return [record["c"] for record in result]

chunks = get_chunks()
print(f"Found {len(chunks)} nodes with label 'Chunk'.")

# --- Generate Embeddings and Upsert Them into the Database ---
for chunk in chunks:
    # Assumes that the text content is stored in the property "content"
    text = chunk
    if text:
        print(f"Embedding node id {chunk.id}...")
        vector = embedder.embed_query(text)
        # Use the node's internal id (or any unique identifier) as the node_id
        node_id = chunk.id  
        upsert_vector(
            driver,
            node_id=node_id,
            embedding_property="embedding",
            vector=vector,
        )
        print(f"Upserted embedding for node id: {node_id}")
    else:
        print(f"Node id {chunk.id} does not have a 'content' property; skipping.")

# --- Close the Connection ---
driver.close()
print("Vector index creation and population complete.")
