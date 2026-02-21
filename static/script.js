const chatBox = document.getElementById("chat-box");
const inputField = document.getElementById("message-input");

let sessionId = localStorage.getItem("session_id");

if (!sessionId) {
    sessionId = Math.random().toString(36).substring(2);
    localStorage.setItem("session_id", sessionId);
}

function appendMessage(message, type) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message");
    messageDiv.classList.add(type === "user" ? "user-message" : "bot-message");
    messageDiv.innerText = message;

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const message = inputField.value.trim();
    if (message === "") return;

    appendMessage(message, "user");
    inputField.value = "";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: sessionId,
                question: message
            })
        });

        const data = await response.json();
        appendMessage(data.answer, "bot");

    } catch (error) {
        appendMessage("Error connecting to server", "bot");
    }
}

inputField.addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});