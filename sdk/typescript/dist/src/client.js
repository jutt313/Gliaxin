import { HttpClient } from './http.js';
import { MemoryNamespace } from './memory.js';
import { AgentNamespace } from './agent.js';
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
 * // Load agent context before an LLM call
 * const ctx = await g.agent.shared('user_123')
 * const systemPrompt = ctx.memories.map(m => `[${m.category}] ${m.content}`).join('\n')
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
}
//# sourceMappingURL=client.js.map