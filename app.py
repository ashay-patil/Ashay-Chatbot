from flask import Flask, request, jsonify
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()
# Configure Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Gemini model
model_gemini = genai.GenerativeModel("models/gemini-2.5-flash")

app = Flask(__name__)

# Load embedding model
embedding_model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

# Load Chroma database
client = chromadb.PersistentClient(path="db")

collection = client.get_or_create_collection(name="mydata")

def get_relevant_context(question):
    question_embedding = embedding_model.encode([question])[0]
    results = collection.query(
        query_embeddings=[question_embedding.tolist()],
        n_results=2
    )

    return " ".join(results["documents"][0])


def generate_answer(question, context):

    prompt = f"""
    Answer the question using only the information provided below.

    Information:
    {context}

    Question:
    {question}
    """

    response = model_gemini.generate_content(prompt)

    return response.text


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("question")
    context = get_relevant_context(question)

    answer = generate_answer(question, context)
    return jsonify({
        "answer": answer
    })

@app.route("/", methods=["GET"])
def hello() :
    return "Hello chatbot"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
