export class MemoryNamespace {
    http;
    constructor(http) {
        this.http = http;
    }
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
    async add(endUserId, content, agentId) {
        return this.http.post('/v1/memory/add', {
            end_user_id: endUserId,
            content,
            ...(agentId && { agent_id: agentId }),
        });
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
    async get(endUserId, options = {}) {
        return this.http.get('/v1/memory/get', {
            end_user_id: endUserId,
            page: options.page ?? 1,
            page_size: options.pageSize ?? 50,
            category: options.category,
            memory_type: options.memoryType,
        });
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
    async search(endUserId, q, options = {}) {
        const data = await this.http.get('/v1/memory/search', {
            end_user_id: endUserId,
            query: q,
            limit: options.limit ?? 10,
            category: options.category,
            min_importance: options.minImportance,
        });
        return data.memories;
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
    async timeline(endUserId, options = {}) {
        return this.http.get('/v1/memory/timeline', {
            end_user_id: endUserId,
            page: options.page ?? 1,
            page_size: options.pageSize ?? 50,
        });
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
    async forget(endUserId) {
        return this.http.delete('/v1/memory/forget', { end_user_id: endUserId });
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
    async conflicts(endUserId, status = 'pending') {
        return this.http.get('/v1/memory/conflicts', {
            end_user_id: endUserId,
            status,
        });
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
    async resolve(conflictId, resolution) {
        return this.http.post('/v1/memory/resolve', {
            conflict_id: conflictId,
            resolution,
        });
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
    async reprocess(endUserId) {
        return this.http.post('/v1/memory/reprocess', { end_user_id: endUserId });
    }
}
//# sourceMappingURL=memory.js.map