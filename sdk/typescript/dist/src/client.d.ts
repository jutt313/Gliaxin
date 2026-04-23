import { MemoryNamespace } from './memory.js';
import { AgentNamespace } from './agent.js';
import type { GliaxinOptions } from './types.js';
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
export declare class Gliaxin {
    readonly memory: MemoryNamespace;
    readonly agent: AgentNamespace;
    constructor(apiKey: string, options?: GliaxinOptions);
}
//# sourceMappingURL=client.d.ts.map