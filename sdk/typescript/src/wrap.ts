/**
 * GliaxinWrapper — one-line turn-aware memory for any LLM.
 *
 * @example
 * import { Gliaxin } from 'gliaxin'
 *
 * const g = new Gliaxin('glx_YOUR_KEY')
 *
 * // Provide YOUR LLM as any async function: (messages: Message[]) => Promise<string>
 * async function myLlm(messages: { role: string; content: string }[]) {
 *   const res = await openai.chat.completions.create({ model: 'gpt-4o', messages })
 *   return res.choices[0].message.content!
 * }
 *
 * // agent_name is required — the wrapper auto-registers it on first use
 * const client = g.wrap(myLlm, { agentName: 'support-bot' })
 *
 * // Memory is automatic. Both user and assistant turns are saved.
 * const reply = await client.chat({ userId: 'user_123', message: 'What do I like?' })
 */

import type { Memory } from './types.js'

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | string
  content: string
}

export type LlmFn = (messages: ChatMessage[]) => Promise<string>

export interface WrapOptions {
  /** Required. Human-readable name for the agent. Auto-registered on first call. */
  agentName: string
  /** Memory scope for saved turns. Default: "agent" (private). */
  scope?: 'agent' | 'project'
  /** Max memories injected per call. Default: 10 */
  contextLimit?: number
  /** Auto-register the agent on first call. Default: true */
  autoRegister?: boolean
  /** Auto-save the full turn after each call. Default: true */
  autoSave?: boolean
  /** Header line prepended before the memory block in the system prompt. */
  systemPrefix?: string
}

export interface ChatOptions {
  /** Your end-user's ID. */
  userId: string
  /** The user's message text. */
  message: string
  /** Optional prior turns for multi-turn context. */
  history?: ChatMessage[]
  /** Optional base system prompt. Memory context is appended to it. */
  system?: string
}

export class GliaxinWrapper {
  private readonly _g: any
  private readonly _llm: LlmFn
  private readonly _agentName: string
  private readonly _scope: 'agent' | 'project'
  private readonly _contextLimit: number
  private readonly _autoRegister: boolean
  private readonly _autoSave: boolean
  private readonly _systemPrefix: string
  private _agentId: string | undefined

  constructor(gliaxin: any, llm: LlmFn, options: WrapOptions) {
    this._g             = gliaxin
    this._llm           = llm
    this._agentName     = options.agentName
    this._scope         = options.scope         ?? 'agent'
    this._contextLimit  = options.contextLimit  ?? 10
    this._autoRegister  = options.autoRegister  ?? true
    this._autoSave      = options.autoSave      ?? true
    this._systemPrefix  = options.systemPrefix  ?? 'You have access to the following memories about this user:'
  }

  private async _ensureRegistered(): Promise<string> {
    if (this._agentId === undefined) {
      const result = await this._g.agent.register(this._agentName)
      this._agentId = result.agent_id
    }
    return this._agentId!
  }

  /**
   * Send a message with automatic memory injection and full-turn auto-save.
   *
   * @example
   * const reply = await client.chat({ userId: 'user_123', message: 'What do I like?' })
   */
  async chat(opts: ChatOptions): Promise<string> {
    const { userId, message, history, system } = opts

    const agentId = this._autoRegister ? await this._ensureRegistered() : this._agentId

    const memories: Memory[] = await this._g.memory.search(userId, message, {
      limit: this._contextLimit,
      agentId,
    })

    const messages = this._buildMessages(message, memories, history, system)

    const reply = await this._llm(messages)

    if (this._autoSave && agentId) {
      await this._saveTurn(userId, agentId, message, reply)
    }

    return reply
  }

  private _buildMessages(
    message: string,
    memories: Memory[],
    history?: ChatMessage[],
    system?: string,
  ): ChatMessage[] {
    const messages: ChatMessage[] = []
    const systemParts: string[] = []

    if (system) systemParts.push(system)

    if (memories.length > 0) {
      const lines = this._systemPrefix ? [this._systemPrefix] : []
      for (const m of memories) {
        lines.push(`- [${m.category}] ${m.content}`)
      }
      systemParts.push(lines.join('\n'))
    }

    if (systemParts.length > 0) {
      messages.push({ role: 'system', content: systemParts.join('\n\n') })
    }

    if (history) messages.push(...history)

    messages.push({ role: 'user', content: message })
    return messages
  }

  private async _saveTurn(userId: string, agentId: string, userMsg: string, assistantReply: string): Promise<void> {
    try {
      await this._g.memory.addTurn(
        userId,
        agentId,
        [
          { role: 'user',      content: userMsg },
          { role: 'assistant', content: assistantReply },
        ],
        { scope: this._scope },
      )
    } catch {
      // save errors never break the caller's response flow
    }
  }
}
