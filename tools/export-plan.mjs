// Fetch the planner's plan from the running tool (headless) and save it.
// usage: node export-plan.mjs <cdpPort> <fileUrl> <outJson>
// then:  node tools/plan-to-header.mjs <outJson> <firmware header>
import { writeFileSync } from "node:fs";

const [CDP, URL, OUT_JSON] = process.argv.slice(2);

const targets = await fetch(`http://127.0.0.1:${CDP}/json/list`).then((r) => r.json());
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); } };
const send = (method, params) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails.exception?.description ?? r.exceptionDetails));
  return r.result?.value;
};

await send("Page.enable");
await send("Page.navigate", { url: URL });
await new Promise((r) => setTimeout(r, 1800));

const json = await evaluate(`window.__exportPlan()`);
writeFileSync(OUT_JSON, JSON.stringify(JSON.parse(json), null, 2));
console.log(`wrote ${OUT_JSON}`);

ws.close();
process.exit(0);
