// Hospoda Gateway — Chrome Extension
// Sleduje queue.json a budí *.AI dívky

const GATEWAY = "http://localhost:8765";

const PERSONAS = {
  "simona.ai": "https://claude.ai/chat/c5f964e5-c9b3-4bcd-9509-3ce406751d2e",
  "sara.ai":   "https://claude.ai/chat/8824991d-a4ad-4e6d-a0b5-a96a3bbd74d7",
  "sofie.ai":  "https://claude.ai/chat/a22aa932-3bf9-4f8a-b4ed-9bcd47491b93",
};

const NUDGE_MSG = "JDI DO HOSPODY";

// Inject skript — spustí se přímo v záložce Claude.AI
function injectNudge(message) {
  // Zkus různé selektory pro Claude.AI input
  const selectors = [
    'div[contenteditable="true"].ProseMirror',
    'div.ProseMirror[contenteditable="true"]',
    'div[contenteditable="true"]',
  ];

  let editor = null;
  for (const sel of selectors) {
    const els = document.querySelectorAll(sel);
    if (els.length > 0) {
      editor = els[els.length - 1];
      break;
    }
  }

  if (!editor) return false;

  editor.focus();
  document.execCommand("selectAll", false, null);
  document.execCommand("delete", false, null);
  document.execCommand("insertText", false, message);

  // Hledej submit tlačítko
  setTimeout(() => {
    const btns = document.querySelectorAll('button');
    let sendBtn = null;
    for (const btn of btns) {
      const label = (btn.getAttribute("aria-label") || "").toLowerCase();
      if (label.includes("send") || label.includes("odeslat")) {
        sendBtn = btn;
        break;
      }
    }
    if (sendBtn) {
      sendBtn.click();
    } else {
      editor.dispatchEvent(new KeyboardEvent("keydown", {
        key: "Enter", bubbles: true, cancelable: true
      }));
    }
  }, 300);

  return true;
}

async function ack(persona) {
  try {
    await fetch(`${GATEWAY}/ack/${persona}`, { method: "POST" });
  } catch (e) {
    console.log("ACK failed:", e);
  }
}

async function getOrOpenTab(url) {
  // Hledej existující záložku
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (tab.url && tab.url.startsWith(url)) return { tab, isNew: false };
  }
  // Otevři novou
  const tab = await chrome.tabs.create({ url, active: false });
  return { tab, isNew: true };
}

async function nudgePersona(persona) {
  const url = PERSONAS[persona];
  console.log(`Budím ${persona}`);

  const { tab, isNew } = await getOrOpenTab(url);

  // Počkej na načtení
  const waitMs = isNew ? 4000 : 800;
  await new Promise(r => setTimeout(r, waitMs));

  // Pokud je záložka stále loading, počkej ještě
  const currentTab = await chrome.tabs.get(tab.id);
  if (currentTab.status !== "complete") {
    await new Promise(r => setTimeout(r, 3000));
  }

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: injectNudge,
      args: [NUDGE_MSG],
    });

    const success = results?.[0]?.result;
    if (success) {
      console.log(`${persona} → nudge odeslán`);
      await ack(persona);
    } else {
      console.log(`${persona} → editor nenalezen, zkusím znovu za chvíli`);
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
    // Gateway není dostupná
  }
}

// Nastav alarm každých 10 sekund (funguje i při uspaném service workeru)
chrome.alarms.create("checkQueue", { periodInMinutes: 1 / 6 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "checkQueue") checkQueue();
});

// Ihned při startu
checkQueue();
