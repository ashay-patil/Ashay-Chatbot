const chatBox       = document.getElementById("chat-box");
const inputField    = document.getElementById("message-input");
const sendBtn       = document.getElementById("send-btn");
const typingEl      = document.getElementById("typing-indicator");
const searchBar     = document.getElementById("search-bar");
const searchInput   = document.getElementById("search-input");

let sessionId = localStorage.getItem("session_id");
if (!sessionId) {
    sessionId = Math.random().toString(36).substring(2);
    localStorage.setItem("session_id", sessionId);
}

let isBotTyping   = false;
let allMessages   = []; // { el, text, type }
let searchVisible = false;

function getTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
    updateSendBtn();
}

function updateSendBtn() {
    const empty = inputField.value.trim() === "";
    sendBtn.classList.toggle("disabled", empty || isBotTyping);
}

function scrollToBottom(smooth = true) {
    chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: smooth ? "smooth" : "instant" });
}

function appendMessage(text, type) {
    const wrap = document.createElement("div");
    wrap.classList.add("message", type === "user" ? "user-message" : "bot-message");

    const bubble = document.createElement("div");
    bubble.classList.add("msg-bubble");
    bubble.textContent = text;

    const meta = document.createElement("div");
    meta.classList.add("msg-meta");
    meta.textContent = getTime();

    if (type === "user") meta.textContent += " ✓✓";

    wrap.appendChild(bubble);
    wrap.appendChild(meta);
    chatBox.appendChild(wrap);

    allMessages.push({ el: wrap, text, type });

    const msgs = chatBox.querySelectorAll(".message");
    wrap.style.animationDelay = "0ms";

    scrollToBottom();
    return wrap;
}

function showTyping() {
    isBotTyping = true;
    typingEl.classList.add("visible");
    updateSendBtn();
    scrollToBottom();
}

function hideTyping() {
    isBotTyping = false;
    typingEl.classList.remove("visible");
    updateSendBtn();
}

async function sendMessage() {
    const message = inputField.value.trim();
    if (!message || isBotTyping) return;

    appendMessage(message, "user");

    inputField.value = "";
    inputField.style.height = "auto";
    inputField.focus();
    updateSendBtn();

    showTyping();

    try {
        const response = await fetch("/chat", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ session_id: sessionId, question: message })
        });

        const data = await response.json();
        hideTyping();

        setTimeout(() => {
            appendMessage(data.answer, "bot");
        }, 80);

    } catch (err) {
        hideTyping();
        setTimeout(() => {
            appendMessage("⚠️ Couldn't reach the server. Please try again.", "bot");
        }, 80);
    }
}

inputField.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

inputField.addEventListener("input", function () {
    autoResize(this);
});

function toggleSearch() {
    searchVisible = !searchVisible;
    searchBar.classList.toggle("visible", searchVisible);
    if (searchVisible) {
        searchInput.focus();
    } else {
        clearSearch();
    }
}

function searchMessages(query) {
    allMessages.forEach(({ el, text }) => {
        el.classList.remove("highlight");
        if (query && text.toLowerCase().includes(query.toLowerCase())) {
            el.classList.add("highlight");
        }
    });

    const first = chatBox.querySelector(".message.highlight");
    if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearSearch() {
    searchInput.value = "";
    allMessages.forEach(({ el }) => el.classList.remove("highlight"));
}

function clearChat() {
    if (!confirm("Clear this conversation?")) return;

    const msgs = chatBox.querySelectorAll(".message, .date-divider");
    msgs.forEach((m, i) => {
        setTimeout(() => {
            m.style.transition = "opacity 0.2s, transform 0.2s";
            m.style.opacity = "0";
            m.style.transform = "scale(0.95)";
        }, i * 30);
    });

    setTimeout(() => {
        chatBox.innerHTML = "";
        allMessages = [];

        const div = document.createElement("div");
        div.className = "date-divider";
        div.innerHTML = "<span>Today</span>";
        chatBox.appendChild(div);

        appendMessage("Hi! I'm Ashay's Chatbot 👋 Ask me anything about Ashay — I'm here to help.", "bot");
    }, msgs.length * 30 + 250);
}

updateSendBtn();
inputField.focus();

const introEl = chatBox.querySelector(".message");
if (introEl) {
    allMessages.push({
        el: introEl,
        text: "Hi! I'm Ashay's Chatbot 👋 Ask me anything about Ashay — I'm here to help.",
        type: "bot"
    });
}