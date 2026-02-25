from os import path

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import jwt
import bcrypt
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_gemini = genai.GenerativeModel("models/gemini-2.5-flash")

# ---------- MongoDB ----------
mongo_client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))
db = mongo_client["chatapp"]
users_col = db["users"]
chats_col = db["chats"]

app = Flask(__name__)
CORS(app)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

# ---------- Embeddings & ChromaDB ----------
embedding_model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
chroma_client = chromadb.PersistentClient(path="db")
collection = chroma_client.get_or_create_collection(name="mydata")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str) -> str:
    payload = {
        "userId": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["userId"]
    except jwt.PyJWTError:
        return None

def get_user_id_from_request() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        return decode_token(token)
    return None

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if users_col.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 409

    user = {
        "email": email,
        "name": name,
        "password": hash_password(password),
        "createdAt": datetime.datetime.utcnow()
    }
    result = users_col.insert_one(user)
    token = create_token(str(result.inserted_id))

    return jsonify({"token": token, "userId": str(result.inserted_id), "name": name}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = users_col.find_one({"email": email})
    if not user or not check_password(password, user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(str(user["_id"]))
    return jsonify({"token": token, "userId": str(user["_id"]), "name": user.get("name", "")}), 200

def get_chroma_context(question: str) -> str:
    question_embedding = embedding_model.encode([question])[0].tolist()
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=10
    )
    return " ".join(results["documents"][0])


def get_chat_history_context(user_id: str, question: str) -> str:
    """Vector search over this user's past chats in MongoDB."""
    question_embedding = embedding_model.encode([question])[0].tolist()

    pipeline1 = [
        {
            "$vectorSearch": {
                "index": "chat_vector_index",
                "path": "questionEmbedding",
                "queryVector": question_embedding,
                "numCandidates": 50,
                "limit": 5,
                "filter": {"userId": user_id}
            }
        },
        {
            "$project": {
                "question": 1,
                "response": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    pipeline2 = [
        {
            "$vectorSearch": {
                "index": "chat_vector_index",
                "path": "responseEmbedding",
                "queryVector": question_embedding,
                "numCandidates": 50,
                "limit": 5,
                "filter": {"userId": user_id}
            }
        },
        {
            "$project": {
                "question": 1,
                "response": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    results1 = list(chats_col.aggregate(pipeline1))
    results2 = list(chats_col.aggregate(pipeline2))
    if not results1 and not results2:
        return ""
    results = results1 + results2
    history_parts = []
    for r in results:
        history_parts.append(f"Q: {r['question']}\nA: {r['response']}")
    return "\n\n".join(history_parts)


def generate_answer(question: str, chroma_context: str, chat_history: str) -> str:
    history_section = f"""
    Relevant past conversation history:
    {chat_history}
    """ if chat_history else ""

    prompt = f"""
    Answer the question using the information and conversation history provided below.

    Information from knowledge base:
    {chroma_context}
    {history_section}

    Question:
    {question}
    """

    response = model_gemini.generate_content(prompt)
    return response.text


@app.route("/chat", methods=["POST"])
def chat():
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    # Get context from both sources
    chroma_context = get_chroma_context(question)
    chat_history_context = get_chat_history_context(user_id, question)

    # Generate answer
    answer = generate_answer(question, chroma_context, chat_history_context)

    # Compute embeddings for storage
    question_embedding = embedding_model.encode([question])[0].tolist()
    response_embedding = embedding_model.encode([answer])[0].tolist()

    chat_doc = {
        "userId": user_id,
        "question": question,
        "response": answer,
        "questionEmbedding": question_embedding,
        "responseEmbedding": response_embedding,
        "createdAt": datetime.datetime.utcnow()
    }
    chats_col.insert_one(chat_doc)

    return jsonify({"answer": answer})


@app.route("/chats", methods=["GET"])
def get_user_chats():
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    chats = list(chats_col.find(
        {"userId": user_id},
        {"question": 1, "response": 1, "createdAt": 1, "_id": 0}
    ).sort("createdAt", -1))

    return jsonify({"chats": chats})


@app.route("/", methods=["GET"])
def hello():
    return render_template("index.html")

@app.route("/login", methods=["GET"])
def loginPage():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def registerPage():
    return render_template("register.html")

@app.route("/getme", methods=["GET"])
def getme():
    user_id = get_user_id_from_request()

    if user_id is None:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
    except:
        return jsonify({"error": "Unauthorized"}), 401

    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({"name": user.get("name", "")})
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    extra_dirs = ['templates','static']
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                filename = path.join(dirname, filename)
                if path.isfile(filename):
                    extra_files.append(filename)
    app.run(host="0.0.0.0", port=port, debug=True, extra_files=extra_files)