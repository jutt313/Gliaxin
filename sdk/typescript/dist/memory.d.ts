import { HttpClient } from './http.js';
import type { AddResult, Memory, MemoryList, ForgetResult, ConflictList, ResolveResult, ReprocessResult, GetMemoryOptions, SearchMemoryOptions, TimelineOptions } from './types.js';
export declare class MemoryNamespace {
    private readonly http;
    constructor(http: HttpClient);
    /**
     * Store a new memory for a user.
     *
     * The raw content is persisted immediately and queued for async
     * Gemini processing (extraction + embedding).
     *
     * @param endUserId - Your user's ID. A vault is auto-created on first add.
     * @param content   - The raw memory text.
     * @param agentId   - Optional agent UUID to attribute the memory to.
     *
     * @example
     * const result = await g.memory.add('user_123', 'User prefers dark mode')
     * console.log(result.raw_id) // "2125bf07-..."
     */
    add(endUserId: string, content: string, agentId?: string): Promise<AddResult>;
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
    get(endUserId: string, options?: GetMemoryOptions): Promise<MemoryList>;
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
    search(endUserId: string, q: string, options?: SearchMemoryOptions): Promise<Memory[]>;
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
    timeline(endUserId: string, options?: TimelineOptions): Promise<MemoryList>;
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
    forget(endUserId: string): Promise<ForgetResult>;
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
    conflicts(endUserId: string, status?: string): Promise<ConflictList>;
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
    resolve(conflictId: string, resolution: 'keep_old' | 'keep_new'): Promise<ResolveResult>;
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
    reprocess(endUserId: string): Promise<ReprocessResult>;
}
//# sourceMappingURL=memory.d.ts.map