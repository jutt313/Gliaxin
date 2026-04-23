import { HttpClient } from './http.js'
import type {
  AgentList, RegisterResult, DeleteResult, MemoryList,
} from './types.js'

export class AgentNamespace {
  constructor(private readonly http: HttpClient) {}

  /**
   * Create a named agent within your project.
   *
   * Idempotent — registering the same name returns the existing agent
   * without creating a duplicate.
   *
   * @param name - Unique agent name within your project.
   *
   * @example
   * const agent = await g.agent.register('support-bot')
   * console.log(agent.agent_id, agent.registered) // true if new
   */
  async register(name: string): Promise<RegisterResult> {
    return this.http.post<RegisterResult>('/v1/agent/register', { name })
  }

  /**
   * List all active agents in your project.
   *
   * @example
   * const result = await g.agent.list()
   * result.agents.forEach(a => console.log(a.name, a.agent_id))
   */
  async list(): Promise<AgentList> {
    return this.http.get<AgentList>('/v1/agent/list')
  }

  /**
   * Soft-delete an agent. The agent will no longer appear in list
   * or register calls.
   *
   * @param agentId - UUID of the agent to delete.
   *
   * @example
   * const result = await g.agent.delete('agent-uuid')
   * console.log(result.deleted) // true
   */
  async delete(agentId: string): Promise<DeleteResult> {
    return this.http.delete<DeleteResult>(`/v1/agent/${agentId}`)
  }

  /**
   * Get all project-scoped active memories for a user, visible to every
   * agent in the project. Sorted by importance — procedural memories first.
   *
   * Use this at the start of every agent turn to load user context.
   *
   * @param endUserId - The user to retrieve shared memories for.
   * @param limit     - Max results (default 50, max 100).
   *
   * @example
   * const context = await g.agent.shared('user_123')
   * const systemPrompt = context.memories
   *   .map(m => `[${m.category}] ${m.content}`)
   *   .join('\n')
   * // Inject systemPrompt into your LLM
   */
  async shared(endUserId: string, limit = 50): Promise<MemoryList> {
    const data = await this.http.get<{ memories: MemoryList['memories']; total: number }>(
      '/v1/agent/shared',
      { end_user_id: endUserId, limit },
    )
    return { memories: data.memories, total: data.total, page: 1, pages: 1 }
  }
}
