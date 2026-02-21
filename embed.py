import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

client = chromadb.PersistentClient(path="db")

collection = client.get_or_create_collection(name="mydata")

# Read bio file
with open("data/bio.txt", "r", encoding="utf-8") as file:
    text = file.read()

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
