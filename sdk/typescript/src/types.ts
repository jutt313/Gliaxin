// ── Memory ─────────────────────────────────────────────────

export type MemoryCategory =
  | 'job'
  | 'ideas'
  | 'problems'
  | 'personal'
  | 'decisions'
  | 'other'

export type MemoryType = 'episodic' | 'semantic' | 'procedural'

export type MemoryStatus = 'active' | 'disputed' | 'superseded'

export interface Memory {
  memory_id: string
  content: string
  category: MemoryCategory
  memory_type: MemoryType
  importance: number
  slot: string | null
  status: MemoryStatus
  scope: string
  agent_id: string | null
  created_at: string
}

export interface MemoryList {
  memories: Memory[]
  total: number
  page: number
  pages: number
}

export interface AddResult {
  raw_id: string
  status: 'queued'
}

export interface AddTurnResult {
  turn_id: string
  raw_ids: string[]
  status: 'queued'
}

export interface TurnMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AddTurnOptions {
  /** "agent" (private, default) or "project" (shared across agents) */
  scope?: 'agent' | 'project'
  /** Optional metadata attached to all raw rows */
  metadata?: Record<string, unknown>
}

export interface ForgetResult {
  deleted: boolean
}

export interface ReprocessResult {
  queued: number
}

// ── Conflicts ──────────────────────────────────────────────

export type ConflictStatus = 'pending' | 'resolved' | 'dismissed'

export interface Conflict {
  conflict_id: string
  slot: string | null
  old_memory: Partial<Memory>
  new_memory: Partial<Memory>
  status: ConflictStatus
  created_at: string
}

export interface ConflictList {
  conflicts: Conflict[]
  total: number
}

export interface ResolveResult {
  resolved: boolean
  winner: string
}

// ── Agents ─────────────────────────────────────────────────

export interface Agent {
  agent_id: string
  name: string
  created_at: string
}

export interface AgentList {
  agents: Agent[]
  total: number
}

export interface RegisterResult {
  agent_id: string
  name: string
  created_at: string
  registered: boolean
}

export interface DeleteResult {
  deleted: boolean
  agent_id: string
}

// ── Options ────────────────────────────────────────────────

export interface GliaxinOptions {
  /** Override the API base URL. Defaults to https://api.gliaxin.com */
  baseUrl?: string
  /** Request timeout in milliseconds. Defaults to 30000. */
  timeout?: number
}

export interface GetMemoryOptions {
  page?: number
  pageSize?: number
  category?: MemoryCategory
  memoryType?: MemoryType
}

export interface SearchMemoryOptions {
  limit?: number
  agentId?: string
  category?: MemoryCategory
  minImportance?: number
}

export interface TimelineOptions {
  page?: number
  pageSize?: number
}

// ── Raw Layer A ────────────────────────────────────────────

export interface RawRecord {
  raw_id: string
  content: string
  processing_status: string
  agent_id: string | null
  created_at: string
  metadata: Record<string, unknown> | null
}

export interface RawList {
  records: RawRecord[]
  total: number
  page: number
  pages: number
}

export interface RawOptions {
  page?: number
  pageSize?: number
  agentId?: string
}

export interface FixResult {
  queued: boolean
  memory_id: string
  raw_id: string
}
