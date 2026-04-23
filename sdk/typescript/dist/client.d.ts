import { MemoryNamespace } from './memory.js';
import { AgentNamespace } from './agent.js';
import { GliaxinWrapper } from './wrap.js';
import type { GliaxinOptions } from './types.js';
import type { LlmFn, WrapOptions } from './wrap.js';
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
export declare class Gliaxin {
    readonly memory: MemoryNamespace;
    readonly agent: AgentNamespace;
    constructor(apiKey: string, options?: GliaxinOptions);
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
    wrap(llm: LlmFn, options?: WrapOptions): GliaxinWrapper;
}
//# sourceMappingURL=client.d.ts.map