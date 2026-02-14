import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="db")
collection = client.get_collection(name="mydata")

model = SentenceTransformer("all-MiniLM-L6-v2")

question = "What are Ashay's skills?"

embedding = model.encode([question])

results = collection.query(
    query_embeddings=embedding.tolist(),
    n_results=2
)

print("Retrieved context:")
print(results["documents"])
