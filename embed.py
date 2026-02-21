import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

client = chromadb.PersistentClient(path="db")

collection = client.get_or_create_collection(name="mydata")

# Read bio file
with open("data/bio.txt", "r", encoding="utf-8") as file:
    text = file.read()


sentences = text.split(". ")

chunks = []
current_chunk = ""

for sentence in sentences:
    if len(current_chunk) + len(sentence) < 300:
        current_chunk += sentence + ". "
    else:
        chunks.append(current_chunk.strip())
        current_chunk = sentence + ". "

if current_chunk:
    chunks.append(current_chunk.strip())

embeddings = model.encode(chunks)


for i in range(len(chunks)):
    collection.add(
ids=[str(i)],
documents=[chunks[i]],
embeddings=[embeddings[i].tolist()]
)


print("Embeddings stored permanently in db folder.")
