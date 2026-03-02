// Hospoda Gateway — Chrome Extension
// Sleduje queue.json a budí *.AI dívky

const GATEWAY = "http://localhost:8765";
const INTERVAL_MS = 10000; // 10 sekund

const PERSONAS = {
  "simona.ai": "https://claude.ai/chat/c5f964e5-c9b3-4bcd-9509-3ce406751d2e",
  "sara.ai":   "https://claude.ai/chat/8824991d-a4ad-4e6d-a0b5-a96a3bbd74d7",
  "sofie.ai":  "https://claude.ai/chat/a22aa932-3bf9-4f8a-b4ed-9bcd47491b93",
};

const NUDGE_MSG = "JDI DO HOSPODY";

// Inject skript — spustí se přímo v záložce Claude.AI
function injectNudge(message) {
  return new Promise((resolve) => {
    // Najdi input (ProseMirror contenteditable)
    const editors = document.querySelectorAll('[contenteditable="true"]');
    const editor = editors[editors.length - 1]; // poslední = input
    if (!editor) { resolve(false); return; }

    editor.focus();
    document.execCommand("selectAll", false, null);
    document.execCommand("delete", false, null);
    document.execCommand("insertText", false, message);

    // Počkej chvilku, pak odešli
    setTimeout(() => {
      // Hledej submit tlačítko
      const btns = document.querySelectorAll('button');
      let sendBtn = null;
      for (const btn of btns) {
        const label = btn.getAttribute("aria-label") || "";
        if (label.toLowerCase().includes("send") || label.toLowerCase().includes("odeslat")) {
          sendBtn = btn;
          break;
        }
      }
      if (!sendBtn) {
        // Fallback: Enter key
        editor.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      } else {
        sendBtn.click();
      }
      resolve(true);
    }, 500);
  });
}

async function ack(persona) {
  try {
    await fetch(`${GATEWAY}/ack/${persona}`, { method: "POST" });
  } catch (e) {
    console.log("ACK failed:", e);
  }
}

async function findOrOpenTab(url) {
  const tabs = await chrome.tabs.query({ url: "https://claude.ai/chat/*" });
  for (const tab of tabs) {
    if (tab.url.startsWith(url)) return tab;
  }
  // Záložka není otevřená — otevři ji
  return await chrome.tabs.create({ url, active: false });
}

async function nudgePersona(persona) {
  const url = PERSONAS[persona];
  console.log(`Budím ${persona} → ${url}`);

  const tab = await findOrOpenTab(url);

  // Počkej na načtení pokud je nová záložka
  await new Promise(resolve => setTimeout(resolve, tab.status === "complete" ? 500 : 3000));

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: injectNudge,
      args: [NUDGE_MSG],
    });

    const success = results?.[0]?.result;
    if (success) {
      console.log(`${persona} → nudge odeslan`);
      await ack(persona);
    } else {
      console.log(`${persona} → editor nenalezen`);
    }
  } catch (e) {
    console.log(`${persona} → chyba:`, e);
  }
}

async function checkQueue() {
  try {
    const resp = await fetch(`${GATEWAY}/queue.json?t=${Date.now()}`);
    if (!resp.ok) return;
    const queue = await resp.json();

    for (const [persona, data] of Object.entries(queue)) {
      if (data.pending) {
        await nudgePersona(persona);
      }
    }
  } catch (e) {
    // Gateway není dostupná — tiše ignoruj
  }
}

// Spusť smyčku
setInterval(checkQueue, INTERVAL_MS);
checkQueue(); // ihned při startu
