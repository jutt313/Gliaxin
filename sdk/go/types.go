package gliaxin

// Memory represents a single processed memory from LayerB.
type Memory struct {
	MemoryID   string   `json:"memory_id"`
	Content    string   `json:"content"`
	Category   string   `json:"category"`
	MemoryType string   `json:"memory_type"`
	Importance float64  `json:"importance"`
	Slot       *string  `json:"slot,omitempty"`
	Status     string   `json:"status"`
	Scope      string   `json:"scope"`
	AgentID    *string  `json:"agent_id,omitempty"`
	CreatedAt  string   `json:"created_at"`
}

// MemoryList is a paginated list of memories.
type MemoryList struct {
	Memories []Memory `json:"memories"`
	Total    int      `json:"total"`
	Page     int      `json:"page"`
	Pages    int      `json:"pages"`
}

// AddResult is returned after successfully saving a legacy single-message memory.
type AddResult struct {
	RawID  string `json:"raw_id"`
	Status string `json:"status"`
}

// AddTurnResult is returned after saving a full conversation turn.
type AddTurnResult struct {
	TurnID string   `json:"turn_id"`
	RawIDs []string `json:"raw_ids"`
	Status string   `json:"status"`
}

// AddTurnOptions controls scope and metadata for Memory.AddTurn.
type AddTurnOptions struct {
	// Scope is "agent" (private, default) or "project" (shared across agents).
	Scope    string
	Metadata map[string]interface{}
}

// SearchMemoryOptions controls filtering for Memory.Search.
type SearchMemoryOptions struct {
	Limit            int
	AgentID          string
	Category         string
	MinImportance    float64
	HasMinImportance bool
}

// ForgetResult is returned after deleting all user data.
type ForgetResult struct {
	Deleted bool `json:"deleted"`
}

// ReprocessResult is returned after queuing a vault rebuild.
type ReprocessResult struct {
	Queued int `json:"queued"`
}

// Conflict represents a detected contradiction between two memories.
type Conflict struct {
	ConflictID string                 `json:"conflict_id"`
	Slot       *string                `json:"slot,omitempty"`
	OldMemory  map[string]interface{} `json:"old_memory"`
	NewMemory  map[string]interface{} `json:"new_memory"`
	Status     string                 `json:"status"`
	CreatedAt  string                 `json:"created_at"`
}

// ConflictList is a list of conflicts with a total count.
type ConflictList struct {
	Conflicts []Conflict `json:"conflicts"`
	Total     int        `json:"total"`
}

// ResolveResult is returned after resolving a conflict.
type ResolveResult struct {
	Resolved bool   `json:"resolved"`
	Winner   string `json:"winner"`
}

// Agent represents a named agent registered within a project.
type Agent struct {
	AgentID   string `json:"agent_id"`
	Name      string `json:"name"`
	CreatedAt string `json:"created_at"`
}

// AgentList is a list of agents with a total count.
type AgentList struct {
	Agents []Agent `json:"agents"`
	Total  int     `json:"total"`
}

// RegisterResult is returned after registering an agent.
type RegisterResult struct {
	AgentID    string `json:"agent_id"`
	Name       string `json:"name"`
	CreatedAt  string `json:"created_at"`
	Registered bool   `json:"registered"`
}

// DeleteResult is returned after deleting an agent.
type DeleteResult struct {
	Deleted bool   `json:"deleted"`
	AgentID string `json:"agent_id"`
}

// Message is a single chat turn used by the Wrap helper.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// RawRecord is a single verbatim Layer A entry.
type RawRecord struct {
	RawID             string                 `json:"raw_id"`
	Content           string                 `json:"content"`
	ProcessingStatus  string                 `json:"processing_status"`
	AgentID           *string                `json:"agent_id,omitempty"`
	CreatedAt         string                 `json:"created_at"`
	Metadata          map[string]interface{} `json:"metadata,omitempty"`
}

// RawList is a paginated list of raw Layer A records.
type RawList struct {
	Records []RawRecord `json:"records"`
	Total   int         `json:"total"`
	Page    int         `json:"page"`
	Pages   int         `json:"pages"`
}

// RawOptions controls pagination and filtering for Memory.Raw.
type RawOptions struct {
	Page     int    // default 1
	PageSize int    // default 50, max 200
	AgentID  string // optional filter
}

// FixResult is returned after reporting a bad memory for re-extraction.
type FixResult struct {
	Queued   bool   `json:"queued"`
	MemoryID string `json:"memory_id"`
	RawID    string `json:"raw_id"`
}

// GetMemoryOptions controls pagination and filtering for Memory.Get.
type GetMemoryOptions struct {
	Page       int    // default 1
	PageSize   int    // default 50, max 100
	Category   string // job | ideas | problems | personal | decisions | other
	MemoryType string // episodic | semantic | procedural
}


// TimelineOptions controls pagination for Memory.Timeline.
type TimelineOptions struct {
	Page     int // default 1
	PageSize int // default 50, max 100
}
