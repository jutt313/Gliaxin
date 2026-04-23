import { HttpClient } from './http.js';
import { MemoryNamespace } from './memory.js';
import { AgentNamespace } from './agent.js';
import { GliaxinWrapper } from './wrap.js';
const DEFAULT_BASE_URL = 'https://api.gliaxin.com';
const DEFAULT_TIMEOUT = 30_000;
/**
 * Gliaxin API client.
 *
 * @example
 * import { Gliaxin } from 'gliaxin'
 *
 * const g = new Gliaxin('glx_YOUR_KEY')
 *
 * // Add a memory
 * const result = await g.memory.add('user_123', 'User prefers dark mode')
 *
 * // Search memories
 * const results = await g.memory.search('user_123', 'UI preferences')
 *
 * // One-line memory wrapper — works with any LLM
 * async function myLlm(messages) { ... }
 * const client = g.wrap(myLlm)
 * const reply = await client.chat({ userId: 'user_123', message: 'What do I like?' })
 */
export class Gliaxin {
    memory;
    agent;
    constructor(apiKey, options = {}) {
        if (!apiKey?.startsWith('glx_')) {
            throw new Error("api_key must start with 'glx_'");
        }
        const http = new HttpClient(apiKey, options.baseUrl ?? DEFAULT_BASE_URL, options.timeout ?? DEFAULT_TIMEOUT);
        this.memory = new MemoryNamespace(http);
        this.agent = new AgentNamespace(http);
    }
    /**
     * Wrap any async LLM function with automatic memory search + save.
     *
     * @param llm     Any async fn: (messages: ChatMessage[]) => Promise<string>
     *                Works with OpenAI, Anthropic, Gemini, Ollama, LiteLLM, etc.
     * @param options Optional config (contextLimit, autoSave, agentId, systemPrefix).
     *
     * @example
     * async function myLlm(messages) {
     *   const res = await openai.chat.completions.create({ model: 'gpt-4o', messages })
     *   return res.choices[0].message.content
     * }
     * const client = g.wrap(myLlm)
     * const reply = await client.chat({ userId: 'user_123', message: 'hello' })
     */
    wrap(llm, options = {}) {
        return new GliaxinWrapper(this, llm, options);
    }
}
//# sourceMappingURL=client.js.map