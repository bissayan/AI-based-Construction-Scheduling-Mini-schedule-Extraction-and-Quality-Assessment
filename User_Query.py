import numpy as np
from py2neo import Graph
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
import re

# Load pre-trained embedding model
embedding_model = SentenceTransformer('intfloat/e5-large')
print("Loaded sentence transformer model: intfloat/e5-large")

# Connect to Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "1234567EH"))
print("Connected to Neo4j database")

def generate_query_embedding(query: str) -> np.ndarray:
    """Generate embedding for a user query"""
    embedding = embedding_model.encode(query, convert_to_numpy=True)
    print(f"Generated embedding for query '{query[:50]}...'")
    return embedding

def find_task_nodes_with_embeddings() -> list:
    """Retrieve all Task nodes with embeddings and durations"""
    results = graph.run("""
        MATCH (n:Task)
        WHERE n.path_embedding_sequence IS NOT NULL AND n.Duration IS NOT NULL
        RETURN n.UID, n.name, n.path_embedding_sequence AS embedding, n.Duration
    """).data()
    print(f"Found {len(results)} Task nodes with embeddings and durations")
    valid_nodes = []
    for result in results:
        node_uid = result.get('n.UID')
        node_name = result.get('n.name')
        node_embedding = result.get('embedding')
        duration = result.get('n.Duration')
        if node_uid and node_name and node_embedding and duration:
            try:
                node_embedding_array = np.array(node_embedding, dtype=np.float32)
                if node_embedding_array.size > 0:
                    # Keep duration format exactly as stored (like "120.0h")
                    valid_nodes.append((node_uid, node_name, node_embedding_array, duration))
            except (ValueError, TypeError):
                continue
    return valid_nodes

def compute_cosine_similarity(query_embedding: np.ndarray, node_embeddings: list) -> list:
    """Compute cosine similarity for all nodes"""
    return cosine_similarity([query_embedding], node_embeddings)[0].tolist()

def process_user_query(query: str, similarity_threshold: float = 0.7):
    """Process user query and write task names with durations and similarity scores to files"""
    print(f"Processing query: '{query}' with similarity threshold {similarity_threshold}")
    
    # Generate query embedding
    query_embedding = generate_query_embedding(query)

    # Find all Task nodes with embeddings and durations
    task_nodes = find_task_nodes_with_embeddings()
    if not task_nodes:
        print("No valid Task nodes found for similarity search")
        return

    # Extract embeddings for similarity computation
    node_embeddings = [emb for _, _, emb, _ in task_nodes]
    if not node_embeddings:
        print("No valid embeddings found for Task nodes")
        return

    # Compute similarities for all nodes
    similarities = compute_cosine_similarity(query_embedding, node_embeddings)

    # Pair nodes with similarities and filter by threshold
    node_pairs = [(node, sim) for (node, sim) in zip(task_nodes, similarities) if sim >= similarity_threshold]
    if not node_pairs:
        print(f"No nodes found with similarity >= {similarity_threshold}")
        return

    # Group by name and keep the node with the highest similarity
    unique_nodes = {}
    for (uid, name, _, duration), sim in node_pairs:
        if name not in unique_nodes or sim > unique_nodes[name][1]:
            unique_nodes[name] = ((uid, name, None, duration), sim)

    # Sort by similarity
    sorted_unique_pairs = sorted(unique_nodes.values(), key=lambda x: x[1], reverse=True)

    # Write task names, durations AND similarity scores to files
    with open("level_similarity.txt", "w") as f:
        f.write(f"Task names and durations for '{query}' (Path_Level) with similarity >= {similarity_threshold}:\n")
        for (uid, name, _, duration), sim in sorted_unique_pairs:
            f.write(f"- {name} (Duration: {duration}, Similarity: {sim:.3f})\n")

    with open("sequence_similarity.txt", "w") as f:
        f.write(f"Task names and durations for '{query}' (Path_Sequence) with similarity >= {similarity_threshold}:\n")
        for (uid, name, _, duration), sim in sorted_unique_pairs:
            f.write(f"- {name} (Duration: {duration}, Similarity: {sim:.3f})\n")

    print(f"Results written to 'level_similarity.txt' and 'sequence_similarity.txt'")

# Example usage
if __name__ == "__main__":
    query = "Ravi is builder and he is working on project. Give him first floor column details"
    process_user_query(query, similarity_threshold=0.7)