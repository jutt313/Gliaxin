import fetch from "node-fetch";

const API_URL = process.env.GLIAXIN_API_URL ?? "http://localhost:9823";
const API_KEY = process.env.GLIAXIN_API_KEY ?? "";
const USER_ID = process.env.GLIAXIN_USER_ID ?? "local";

async function searchMemory(query: string, limit = 5): Promise<string[]> {
  const url = `${API_URL}/v1/memory/search?query=${encodeURIComponent(query)}&end_user_id=${encodeURIComponent(USER_ID)}&limit=${limit}`;
  try {
    const res = await fetch(url, {
      headers: { "X-Api-Key": API_KEY },
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return [];
    const data = (await res.json()) as { memories?: { content: string }[] };
    return (data.memories ?? []).map((m) => m.content).filter(Boolean);
  } catch {
    return [];
  }
}

async function saveMemory(userMessage: string, assistantMessage: string): Promise<void> {
  try {
    await fetch(`${API_URL}/v1/memory/add`, {
      method: "POST",
      headers: { "X-Api-Key": API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({
        end_user_id: USER_ID,
        messages: [
          { role: "user", content: userMessage },
          { role: "assistant", content: assistantMessage },
        ],
      }),
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    // non-fatal: memory save failure does not block the agent
  }
}

/**
 * beforePrompt — called before the user prompt is sent to the model.
 * Injects relevant memories as a context prefix.
 */
export async function beforePrompt(ctx: {
  prompt: string;
  [key: string]: unknown;
}): Promise<{ prompt: string }> {
  const memories = await searchMemory(ctx.prompt);
  if (memories.length === 0) return { prompt: ctx.prompt };

  const block = [
    "--- Gliaxin Memory ---",
    ...memories,
    "--- End Memory ---",
    "",
    ctx.prompt,
  ].join("\n");

  return { prompt: block };
}

/**
 * afterResponse — called after the model produces a response.
 * Saves the turn for future memory extraction.
 */
export async function afterResponse(ctx: {
  prompt: string;
  response: string;
  [key: string]: unknown;
}): Promise<void> {
  await saveMemory(ctx.prompt, ctx.response);
}
