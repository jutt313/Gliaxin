/**
 * GliaxinWrapper — one-line memory for any LLM.
 *
 * @example
 * import { Gliaxin } from 'gliaxin'
 *
 * const g = new Gliaxin('glx_YOUR_KEY')
 *
 * // Provide YOUR LLM as any async function: (messages: Message[]) => Promise<string>
 * async function myLlm(messages: { role: string; content: string }[]) {
 *   // OpenAI, Anthropic, Gemini, Ollama, LiteLLM — anything
 *   const res = await openai.chat.completions.create({ model: 'gpt-4o', messages })
 *   return res.choices[0].message.content!
 * }
 *
 * const client = g.wrap(myLlm)
 *
 * // That's it. Memory is automatic.
 * const reply = await client.chat({ userId: 'user_123', message: 'What do I like?' })
 */
export class GliaxinWrapper {
    _g;
    _llm;
    _contextLimit;
    _autoSave;
    _agentId;
    _systemPrefix;
    constructor(gliaxin, llm, options = {}) {
        this._g = gliaxin;
        this._llm = llm;
        this._contextLimit = options.contextLimit ?? 10;
        this._autoSave = options.autoSave ?? true;
        this._agentId = options.agentId;
        this._systemPrefix = options.systemPrefix ?? 'You have access to the following memories about this user:';
    }
    /**
     * Send a message with automatic memory injection and auto-save.
     *
     * @example
     * const reply = await client.chat({ userId: 'user_123', message: 'What do I like?' })
     */
    async chat(opts) {
        const { userId, message, history, system } = opts;
        const memories = await this._g.memory.search(userId, message, {
            limit: this._contextLimit,
        });
        const messages = this._buildMessages(message, memories, history, system);
        const reply = await this._llm(messages);
        if (this._autoSave) {
            this._saveTurn(userId, message, reply).catch(() => { });
        }
        return reply;
    }
    _buildMessages(message, memories, history, system) {
        const messages = [];
        const systemParts = [];
        if (system)
            systemParts.push(system);
        if (memories.length > 0) {
            const lines = this._systemPrefix ? [this._systemPrefix] : [];
            for (const m of memories) {
                lines.push(`- [${m.category}] ${m.content}`);
            }
            systemParts.push(lines.join('\n'));
        }
        if (systemParts.length > 0) {
            messages.push({ role: 'system', content: systemParts.join('\n\n') });
        }
        if (history)
            messages.push(...history);
        messages.push({ role: 'user', content: message });
        return messages;
    }
    async _saveTurn(userId, userMsg, reply) {
        await Promise.all([
            this._g.memory.add(userId, `User: ${userMsg}`, { agentId: this._agentId }),
            this._g.memory.add(userId, `Assistant: ${reply}`, { agentId: this._agentId }),
        ]);
    }
}
//# sourceMappingURL=wrap.js.map