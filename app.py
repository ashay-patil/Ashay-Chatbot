from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model_gemini = genai.GenerativeModel("models/gemini-2.5-flash")

app = Flask(__name__)
CORS(app)
embedding_model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

client = chromadb.PersistentClient(path="db")

collection = client.get_or_create_collection(name="mydata")

def get_relevant_context(question):
    question_embedding = embedding_model.encode([question])[0]
    results = collection.query(
        query_embeddings=[question_embedding.tolist()],
        n_results=4
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
    print(question)
    context = get_relevant_context(question)
    print(question)

    answer = generate_answer(question, context)
    print(answer)
    return jsonify({
        "answer": answer
    })

@app.route("/", methods=["GET"])
def hello() :
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
