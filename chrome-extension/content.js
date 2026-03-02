// content.js — sleduje nové zprávy asistenta na claude.ai
// Posílá je do background.js který zobrazí Chrome notifikaci

let lastMessageText = null;

function getLastAssistantMessage() {
  const messages = document.querySelectorAll('[class*="font-claude-response"]');
  if (messages.length === 0) return null;
  const last = messages[messages.length - 1];
  return last.innerText?.trim() || null;
}

function onNewMessage(text) {
  if (!text || text === lastMessageText) return;
  lastMessageText = text;
  chrome.runtime.sendMessage({
    type: "NEW_ASSISTANT_MESSAGE",
    text: text,
    url: window.location.href,
  });
}

// Sleduj přidávání nových uzlů do DOM
const observer = new MutationObserver(() => {
  const text = getLastAssistantMessage();
  if (text) onNewMessage(text);
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
});
