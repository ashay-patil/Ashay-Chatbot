import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Create persistent client (THIS IS THE CORRECT WAY NOW)
client = chromadb.PersistentClient(path="db")

# Create or get collection
collection = client.get_or_create_collection(name="mydata")

# Read bio file
with open("data/bio.txt", "r", encoding="utf-8") as file:
    text = file.read()

# Split into paragraphs
paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

# Generate embeddings
embeddings = model.encode(paragraphs)

# Store embeddings
for i in range(len(paragraphs)):
    collection.add(
        ids=[str(i)],
        documents=[paragraphs[i]],
        embeddings=[embeddings[i].tolist()]
    )

print("Embeddings stored permanently in db folder.")
