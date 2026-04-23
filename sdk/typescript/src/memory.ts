import { HttpClient } from './http.js'
import type {
  AddResult, AddTurnResult, AddTurnOptions, TurnMessage,
  Memory, MemoryList, ForgetResult,
  Conflict, ConflictList, ResolveResult, ReprocessResult,
  GetMemoryOptions, SearchMemoryOptions, TimelineOptions,
  RawList, RawOptions, FixResult,
} from './types.js'

export class MemoryNamespace {
  constructor(private readonly http: HttpClient) {}

  /**
   * Save a full conversation turn (user + assistant) attributed to an agent.
   *
   * Both sides of the turn are stored as raw evidence; the worker extracts
   * durable memories from the full context. This is the primary ingest method
   * for wrapper-based memory.
   *
   * @param endUserId - Your user's ID.
   * @param agentId   - Required. UUID of the registered agent writing this memory.
   * @param messages  - Ordered list of {role, content} pairs.
   * @param options   - scope ("agent"|"project") and optional metadata.
   *
   * @example
   * const result = await g.memory.addTurn('user_123', agentId, [
   *   { role: 'user', content: 'I prefer dark mode' },
   *   { role: 'assistant', content: 'Noted, I will keep that in mind.' },
   * ])
   * console.log(result.turn_id)
   */
  async addTurn(
    endUserId: string,
    agentId: string,
    messages: TurnMessage[],
    options: AddTurnOptions = {},
  ): Promise<AddTurnResult> {
    return this.http.post<AddTurnResult>('/v1/memory/add', {
      end_user_id: endUserId,
      agent_id: agentId,
      messages,
      scope: options.scope ?? 'agent',
      ...(options.metadata && { metadata: options.metadata }),
    })
  }

  /**
   * [Deprecated] Store a single raw message.
   *
   * Prefer addTurn() which captures the full conversation turn and
   * requires an agent_id for proper memory isolation.
   *
   * @param endUserId - Your user's ID. A vault is auto-created on first add.
   * @param content   - The raw memory text.
   * @param agentId   - Optional agent UUID.
   */
  async add(endUserId: string, content: string, agentId?: string): Promise<AddResult> {
    return this.http.post<AddResult>('/v1/memory/add', {
      end_user_id: endUserId,
      content,
      ...(agentId && { agent_id: agentId }),
    })
  }

  /**
   * List all active memories for a user, ordered by importance descending.
   *
   * @param endUserId - The user whose memories to retrieve.
   * @param options   - Pagination and filter options.
   *
   * @example
   * const result = await g.memory.get('user_123')
   * result.memories.forEach(m => console.log(m.category, m.content))
   */
  async get(endUserId: string, options: GetMemoryOptions = {}): Promise<MemoryList> {
    return this.http.get<MemoryList>('/v1/memory/get', {
      end_user_id: endUserId,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 50,
      category: options.category,
      memory_type: options.memoryType,
    })
  }

  /**
   * Semantic search over a user's memories using vector similarity.
   *
   * @param endUserId - The user to search memories for.
   * @param q         - Natural language search query.
   * @param options   - Limit, category, and importance filters.
   *
   * @example
   * const results = await g.memory.search('user_123', 'language preferences')
   * results.forEach(m => console.log(m.content, m.importance))
   */
  async search(endUserId: string, q: string, options: SearchMemoryOptions = {}): Promise<Memory[]> {
    const data = await this.http.get<{ memories: Memory[] }>('/v1/memory/search', {
      end_user_id: endUserId,
      query: q,
      limit: options.limit ?? 10,
      ...(options.agentId && { agent_id: options.agentId }),
      category: options.category,
      min_importance: options.minImportance,
    })
    return data.memories
  }

  /**
   * Full memory history including disputed/superseded entries, ordered
   * chronologically. Useful for auditing or building an as-of view.
   *
   * @param endUserId - The user whose timeline to retrieve.
   * @param options   - Pagination options.
   *
   * @example
   * const history = await g.memory.timeline('user_123')
   * history.memories.forEach(m => console.log(m.created_at, m.status, m.content))
   */
  async timeline(endUserId: string, options: TimelineOptions = {}): Promise<MemoryList> {
    return this.http.get<MemoryList>('/v1/memory/timeline', {
      end_user_id: endUserId,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 50,
    })
  }

  /**
   * Permanently delete all memories and the vault for a user.
   * Irreversible. Use for GDPR right-to-erasure requests.
   *
   * @param endUserId - The user whose entire memory vault to delete.
   *
   * @example
   * const result = await g.memory.forget('user_123')
   * console.log(result.deleted) // true
   */
  async forget(endUserId: string): Promise<ForgetResult> {
    return this.http.delete<ForgetResult>('/v1/memory/forget', { end_user_id: endUserId })
  }

  /**
   * List memory conflicts for a user.
   *
   * A conflict is created when two memories share the same slot.
   * The new memory waits as 'disputed' while the old stays 'active'.
   *
   * @param endUserId - The user whose conflicts to list.
   * @param status    - Filter by: pending | resolved | dismissed (default: pending).
   *
   * @example
   * const result = await g.memory.conflicts('user_123')
   * result.conflicts.forEach(c => console.log(c.slot, c.old_memory, c.new_memory))
   */
  async conflicts(endUserId: string, status = 'pending'): Promise<ConflictList> {
    return this.http.get<ConflictList>('/v1/memory/conflicts', {
      end_user_id: endUserId,
      status,
    })
  }

  /**
   * Resolve a memory conflict.
   *
   * @param conflictId - UUID of the conflict to resolve.
   * @param resolution - "keep_old" or "keep_new".
   *
   * @example
   * const result = await g.memory.resolve('conflict-uuid', 'keep_new')
   * console.log(result.winner)
   */
  async resolve(conflictId: string, resolution: 'keep_old' | 'keep_new'): Promise<ResolveResult> {
    return this.http.post<ResolveResult>('/v1/memory/resolve', {
      conflict_id: conflictId,
      resolution,
    })
  }

  /**
   * Re-run Gemini extraction and embedding on all raw records for a user.
   * Use when the model is upgraded or to rebuild LayerB from scratch.
   *
   * @param endUserId - The user whose vault to reprocess.
   *
   * @example
   * const result = await g.memory.reprocess('user_123')
   * console.log(`${result.queued} records queued`)
   */
  /**
   * Read Layer A verbatim records — the exact words the user said.
   *
   * No AI processing. Returns raw content + timestamps straight from
   * the immutable store. Useful for debugging or when the agent needs
   * the literal transcript rather than extracted facts.
   *
   * @param endUserId - The user whose raw records to retrieve.
   * @param options   - Pagination and optional agent filter.
   *
   * @example
   * const result = await g.memory.raw('user_123')
   * result.records.forEach(r => console.log(r.created_at, r.content))
   */
  async raw(endUserId: string, options: RawOptions = {}): Promise<RawList> {
    return this.http.get<RawList>('/v1/memory/raw', {
      end_user_id: endUserId,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 50,
      agent_id: options.agentId,
    })
  }

  /**
   * Report a specific Layer B memory as wrong or inaccurate.
   *
   * Deletes the bad processed record and resets the linked raw Layer A
   * entry to pending so the worker re-extracts it cleanly.
   *
   * @param memoryId - UUID of the Layer B memory to fix.
   * @param reason   - Optional description of what is wrong (logged to audit).
   *
   * @example
   * const result = await g.memory.fix('mem-uuid', 'Wrong category assigned')
   * console.log(result.queued)   // true
   * console.log(result.raw_id)   // the raw record that will be re-extracted
   */
  async fix(memoryId: string, reason?: string): Promise<FixResult> {
    return this.http.post<FixResult>('/v1/memory/fix', {
      memory_id: memoryId,
      ...(reason && { reason }),
    })
  }

  async reprocess(endUserId: string): Promise<ReprocessResult> {
    return this.http.post<ReprocessResult>('/v1/memory/reprocess', { end_user_id: endUserId })
  }
}
