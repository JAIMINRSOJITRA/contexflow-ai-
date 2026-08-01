/**
 * ContextFlow AI — Studio Frontend Client
 */

let currentSessionId = null;
let currentChatHistory = [];

document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  loadDocuments();
  loadHistoryList();

  document.getElementById("btn-send").addEventListener("click", sendQuestion);
  document.getElementById("input-question").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  });

  document.getElementById("btn-new-chat").addEventListener("click", startNewChat);
  document.getElementById("btn-close-modal").addEventListener("click", closeEvalModal);
  document.getElementById("btn-close-doc-modal").addEventListener("click", closeDocModal);
  document.getElementById("btn-export-chat").addEventListener("click", exportChat);
});

function showToast(message) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => container.removeChild(toast), 300);
  }, 3000);
}

function useSuggestion(promptText) {
  const input = document.getElementById("input-question");
  input.value = promptText;
  sendQuestion();
}

function startNewChat() {
  currentSessionId = null;
  currentChatHistory = [];
  document.getElementById("chat-canvas").innerHTML = `
    <div class="message assistant">
      <div class="message-avatar">AI</div>
      <div class="message-bubble">
        Hello! I'm <strong>ContextFlow AI</strong>. Upload a document (.pdf, .txt, .docx) above or click one of the quick suggestions below to start asking questions grounded in your knowledge base!
        <div class="suggestions-grid">
          <div class="suggestion-card" onclick="useSuggestion('What is our employee leave & PTO policy?')">
            💡 What is our employee leave & PTO policy?
          </div>
          <div class="suggestion-card" onclick="useSuggestion('Summarize the key terms in our policy documents.')">
            📋 Summarize key terms in policy documents
          </div>
          <div class="suggestion-card" onclick="useSuggestion('What are the security and password rotation requirements?')">
            🔒 What are the security & password rules?
          </div>
        </div>
      </div>
    </div>
  `;
  document.getElementById("badge-latency").innerText = "⚡ Ready";
  showToast("Started new conversation session");
}

/* Document Management */
async function loadDocuments() {
  try {
    const res = await fetch("/api/v1/documents");
    const docs = await res.json();
    const container = document.getElementById("document-list");
    container.innerHTML = "";

    document.getElementById("stat-docs-count").innerText = docs.length;

    if (docs.length === 0) {
      container.innerHTML = '<div style="font-size:12px; color:var(--text-muted); padding:8px;">No documents uploaded yet.</div>';
      return;
    }

    docs.forEach(doc => {
      const item = document.createElement("div");
      item.className = "doc-item";
      item.innerHTML = `
        <span onclick="viewDocDetails(${doc.id}, '${escapeHtml(doc.filename)}', '${doc.uploaded_at}')" title="${doc.filename}">📄 ${doc.filename.length > 18 ? doc.filename.substring(0, 16) + '...' : doc.filename}</span>
        <button class="btn-delete-doc" onclick="deleteDocument(${doc.id})">✕</button>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load documents:", err);
  }
}

function viewDocDetails(id, filename, uploadedAt) {
  const modal = document.getElementById("doc-modal");
  const modalContent = document.getElementById("doc-modal-content");
  modal.classList.add("active");

  modalContent.innerHTML = `
    <div><strong>Filename:</strong> ${filename}</div>
    <div><strong>Document ID:</strong> #${id}</div>
    <div><strong>Indexed At:</strong> ${new Date(uploadedAt).toLocaleString()}</div>
    <div><strong>Status:</strong> Active in FAISS Vector Store</div>
  `;
}

function closeDocModal() {
  document.getElementById("doc-modal").classList.remove("active");
}

async function deleteDocument(id) {
  if (!confirm("Are you sure you want to delete this document and its indexed vectors?")) return;
  try {
    const res = await fetch(`/api/v1/documents/${id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Document deleted successfully");
      loadDocuments();
    } else {
      alert("Failed to delete document.");
    }
  } catch (err) {
    console.error("Delete error:", err);
  }
}

function initDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      uploadFile(fileInput.files[0]);
    }
  });
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const dropzoneText = document.getElementById("dropzone-text");
  const originalText = dropzoneText.innerHTML;
  dropzoneText.innerHTML = `⏳ Uploading and indexing <strong>${file.name}</strong>...`;

  try {
    const res = await fetch("/api/v1/documents/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (res.ok) {
      dropzoneText.innerHTML = `✅ Successfully indexed <strong>${file.name}</strong> (${data.chunks_created} chunks created)`;
      showToast(`Indexed ${file.name} (${data.chunks_created} chunks)`);
      loadDocuments();
      setTimeout(() => dropzoneText.innerHTML = originalText, 4000);
    } else {
      alert(`Upload error: ${data.detail}`);
      dropzoneText.innerHTML = originalText;
    }
  } catch (err) {
    alert("Failed to upload file.");
    dropzoneText.innerHTML = originalText;
  }
}

/* Chat & Question Answering */
async function sendQuestion() {
  const input = document.getElementById("input-question");
  const question = input.value.trim();
  if (!question) return;

  const provider = document.getElementById("provider-select").value;
  input.value = "";

  appendMessage("user", question);
  currentChatHistory.push({ role: "User", text: question });

  const canvas = document.getElementById("chat-canvas");
  const loadingBubble = document.createElement("div");
  loadingBubble.className = "message assistant";
  loadingBubble.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-bubble">⏳ Analyzing context & generating grounded answer...</div>
  `;
  canvas.appendChild(loadingBubble);
  canvas.scrollTop = canvas.scrollHeight;

  try {
    const payload = { question, provider };
    if (currentSessionId) payload.session_id = currentSessionId;

    const res = await fetch("/api/v1/chat/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    canvas.removeChild(loadingBubble);

    if (res.ok) {
      currentSessionId = data.session_id;
      currentChatHistory.push({ role: "ContextFlow AI", text: data.answer, sources: data.sources });
      appendAssistantMessage(data, question);
      document.getElementById("badge-latency").innerText = `⚡ ${data.latency_ms}ms (${data.provider})`;
      loadHistoryList();
    } else {
      appendMessage("assistant", `⚠️ Error: ${data.detail}`);
    }
  } catch (err) {
    canvas.removeChild(loadingBubble);
    appendMessage("assistant", "⚠️ Failed to reach the server.");
  }
}

function appendMessage(role, text) {
  const canvas = document.getElementById("chat-canvas");
  const msg = document.createElement("div");
  msg.className = `message ${role}`;
  msg.innerHTML = `
    <div class="message-avatar">${role === 'user' ? 'U' : 'AI'}</div>
    <div class="message-bubble">${escapeHtml(text)}</div>
  `;
  canvas.appendChild(msg);
  canvas.scrollTop = canvas.scrollHeight;
}

function appendAssistantMessage(data, originalQuestion) {
  const canvas = document.getElementById("chat-canvas");
  const msg = document.createElement("div");
  msg.className = "message assistant";

  let sourcesHtml = "";
  if (data.sources && data.sources.length) {
    sourcesHtml = '<div style="margin-top:10px;">' +
      data.sources.map(s => `<span class="source-tag">📄 ${escapeHtml(s)}</span>`).join('') +
      '</div>';
  }

  const encodedAnswer = encodeURIComponent(data.answer);
  const encodedQuestion = encodeURIComponent(originalQuestion);

  msg.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-bubble">
      <div>${formatMarkdown(data.answer)}</div>
      ${sourcesHtml}
      <div class="message-actions">
        <button class="btn-action" onclick="sendFeedback(${data.message_id}, 'up')">👍 Useful</button>
        <button class="btn-action" onclick="sendFeedback(${data.message_id}, 'down')">👎 Needs Work</button>
        <button class="btn-action" onclick="readAloud('${encodedAnswer}')">🔊 Read Aloud</button>
        <button class="btn-action" onclick="triggerRagasModal('${encodedQuestion}', '${encodedAnswer}')">📊 Run Ragas Eval</button>
      </div>
    </div>
  `;
  canvas.appendChild(msg);
  canvas.scrollTop = canvas.scrollHeight;
}

function readAloud(encodedAnswer) {
  const text = decodeURIComponent(encodedAnswer);
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
    showToast("Playing response audio");
  } else {
    alert("Speech synthesis is not supported in this browser.");
  }
}

async function sendFeedback(messageId, rating) {
  if (!messageId) return;
  try {
    const res = await fetch("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId, rating }),
    });
    if (res.ok) showToast(`Feedback recorded: ${rating}`);
  } catch (err) {
    console.error("Feedback error:", err);
  }
}

function exportChat() {
  if (currentChatHistory.length === 0) {
    alert("No chat conversation to export.");
    return;
  }

  let content = "# ContextFlow AI — Exported Chat Session\n\n";
  currentChatHistory.forEach(msg => {
    content += `### ${msg.role}\n${msg.text}\n`;
    if (msg.sources && msg.sources.length) {
      content += `**Sources:** ${msg.sources.join(', ')}\n`;
    }
    content += "\n---\n\n";
  });

  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `contextflow_chat_${currentSessionId ? currentSessionId.substring(0, 8) : 'session'}.md`;
  a.click();
  URL.revokeObjectURL(url);
  showToast("Exported chat session to Markdown file");
}

/* Ragas Evaluation Modal */
async function triggerRagasModal(encodedQuestion, encodedAnswer) {
  const question = decodeURIComponent(encodedQuestion);
  const answer = decodeURIComponent(encodedAnswer);

  const modal = document.getElementById("eval-modal");
  const modalContent = document.getElementById("eval-modal-content");
  modal.classList.add("active");

  modalContent.innerHTML = `<div>⏳ Calculating Ragas scores with LLM Judge (Groq)...</div>`;

  try {
    const res = await fetch("/api/v1/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        answer,
        contexts: [answer]
      }),
    });

    const data = await res.json();
    if (res.ok) {
      modalContent.innerHTML = `
        <div class="eval-metric-row">
          <span>Faithfulness</span>
          <div class="metric-bar-bg"><div class="metric-bar-fill" style="width:${(data.faithfulness * 100).toFixed(0)}%;"></div></div>
          <strong>${(data.faithfulness * 100).toFixed(0)}%</strong>
        </div>
        <div class="eval-metric-row">
          <span>Answer Relevancy</span>
          <div class="metric-bar-bg"><div class="metric-bar-fill" style="width:${(data.answer_relevancy * 100).toFixed(0)}%;"></div></div>
          <strong>${(data.answer_relevancy * 100).toFixed(0)}%</strong>
        </div>
        <div class="eval-metric-row">
          <span>Context Precision</span>
          <div class="metric-bar-bg"><div class="metric-bar-fill" style="width:${(data.context_precision * 100).toFixed(0)}%;"></div></div>
          <strong>${(data.context_precision * 100).toFixed(0)}%</strong>
        </div>
        <div class="eval-metric-row">
          <span>Context Recall</span>
          <div class="metric-bar-bg"><div class="metric-bar-fill" style="width:${(data.context_recall * 100).toFixed(0)}%;"></div></div>
          <strong>${(data.context_recall * 100).toFixed(0)}%</strong>
        </div>
      `;
    } else {
      modalContent.innerHTML = `<div style="color:var(--danger);">Evaluation failed: ${data.detail}</div>`;
    }
  } catch (err) {
    modalContent.innerHTML = `<div style="color:var(--danger);">Could not connect to evaluation service.</div>`;
  }
}

function closeEvalModal() {
  document.getElementById("eval-modal").classList.remove("active");
}

async function loadHistoryList() {
  try {
    const res = await fetch("/api/v1/chat/sessions");
    if (!res.ok) return;
    const sessions = await res.json();
    const container = document.getElementById("history-list");
    container.innerHTML = "";

    if (sessions.length === 0) {
      container.innerHTML = '<div style="font-size:12px; color:var(--text-muted); padding:8px;">No chat sessions yet.</div>';
      return;
    }

    sessions.forEach(sess => {
      const item = document.createElement("div");
      const isCurrent = sess.session_id === currentSessionId;
      item.className = "history-item";
      if (isCurrent) {
        item.style.borderColor = "var(--accent-indigo)";
        item.style.background = "rgba(99,102,241,0.15)";
      }
      const title = sess.last_question.length > 25 ? sess.last_question.substring(0, 23) + "..." : sess.last_question;
      item.innerHTML = `
        <span onclick="loadSession('${sess.session_id}')" title="${escapeHtml(sess.last_question)}">💬 ${escapeHtml(title)}</span>
        <button class="btn-delete-doc" onclick="event.stopPropagation(); deleteSession('${sess.session_id}')">✕</button>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load history list:", err);
  }
}

async function loadSession(sessionId) {
  try {
    const res = await fetch(`/api/v1/chat/history/${sessionId}`);
    if (!res.ok) return;
    const history = await res.json();

    currentSessionId = sessionId;
    currentChatHistory = [];
    const canvas = document.getElementById("chat-canvas");
    canvas.innerHTML = "";

    history.forEach(item => {
      appendMessage("user", item.question);
      currentChatHistory.push({ role: "User", text: item.question });
      appendAssistantMessage({ answer: item.answer, sources: item.sources }, item.question);
      currentChatHistory.push({ role: "ContextFlow AI", text: item.answer, sources: item.sources });
    });

    loadHistoryList();
    showToast("Loaded past conversation session");
  } catch (err) {
    console.error("Failed to load session:", err);
  }
}

async function deleteSession(sessionId) {
  if (!confirm("Are you sure you want to delete this chat session?")) return;
  try {
    const res = await fetch(`/api/v1/chat/history/${sessionId}`, { method: "DELETE" });
    if (res.ok) {
      if (currentSessionId === sessionId) {
        startNewChat();
      } else {
        loadHistoryList();
      }
      showToast("Deleted chat session");
    }
  } catch (err) {
    console.error("Delete session error:", err);
  }
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}

function formatMarkdown(text) {
  return escapeHtml(text)
    .replace(/^### (.*$)/gim, '<h3 style="margin:10px 0 6px; font-size:15px; color:#a5b4fc;">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 style="margin:12px 0 8px; font-size:16px; color:#c084fc;">$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\- (.*$)/gim, '<li style="margin-left:16px;">$1</li>')
    .replace(/\n/g, '<br>');
}
