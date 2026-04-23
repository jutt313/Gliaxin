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
export interface ChatMessage {
    role: 'system' | 'user' | 'assistant' | string;
    content: string;
}
export type LlmFn = (messages: ChatMessage[]) => Promise<string>;
export interface WrapOptions {
    /** Max memories injected per call. Default: 10 */
    contextLimit?: number;
    /** Auto-save user + assistant turn after each call. Default: true */
    autoSave?: boolean;
    /** Optional agent UUID to attribute saved memories to. */
    agentId?: string;
    /** Header line prepended before the memory block in the system prompt. */
    systemPrefix?: string;
}
export interface ChatOptions {
    /** Your end-user's ID. */
    userId: string;
    /** The user's message text. */
    message: string;
    /** Optional prior turns for multi-turn context. */
    history?: ChatMessage[];
    /** Optional base system prompt. Memory context is appended to it. */
    system?: string;
}
export declare class GliaxinWrapper {
    private readonly _g;
    private readonly _llm;
    private readonly _contextLimit;
    private readonly _autoSave;
    private readonly _agentId;
    private readonly _systemPrefix;
    constructor(gliaxin: any, llm: LlmFn, options?: WrapOptions);
    /**
     * Send a message with automatic memory injection and auto-save.
     *
     * @example
     * const reply = await client.chat({ userId: 'user_123', message: 'What do I like?' })
     */
    chat(opts: ChatOptions): Promise<string>;
    private _buildMessages;
    private _saveTurn;
}
//# sourceMappingURL=wrap.d.ts.map