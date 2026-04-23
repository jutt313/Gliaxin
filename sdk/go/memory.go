package gliaxin

import (
	"context"
	"fmt"
)

// MemoryNamespace groups all /v1/memory/* operations.
// Access via client.Memory.
type MemoryNamespace struct {
	http *httpClient
}

// AddTurn saves a full conversation turn (user + assistant) attributed to an agent.
//
// Both sides of the turn are stored as raw evidence; the worker extracts durable
// memories from the full context. This is the primary ingest method for
// wrapper-based memory. agentID is required.
//
// Use opts.Scope = "agent" (default) for private memory or "project" for shared.
//
// Example:
//
//	result, err := g.Memory.AddTurn(ctx, "user_123", agentID, []gliaxin.Message{
//	    {Role: "user",      Content: "I prefer dark mode"},
//	    {Role: "assistant", Content: "Noted."},
//	}, gliaxin.AddTurnOptions{})
//	fmt.Println(result.TurnID)
func (m *MemoryNamespace) AddTurn(ctx context.Context, endUserID, agentID string, messages []Message, opts AddTurnOptions) (*AddTurnResult, error) {
	if agentID == "" {
		return nil, fmt.Errorf("gliaxin: agent_id is required for AddTurn")
	}
	scope := opts.Scope
	if scope == "" {
		scope = "agent"
	}
	body := map[string]interface{}{
		"end_user_id": endUserID,
		"agent_id":    agentID,
		"messages":    messages,
		"scope":       scope,
	}
	if opts.Metadata != nil {
		body["metadata"] = opts.Metadata
	}
	var out AddTurnResult
	if err := m.http.post(ctx, "/v1/memory/add", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Add stores a single raw message for a user.
//
// Deprecated: prefer AddTurn which captures the full conversation turn and
// requires an agentID for proper memory isolation.
//
// agentID is optional — pass "" to skip attribution.
//
// Example:
//
//	result, err := g.Memory.Add(ctx, "user_123", "User prefers dark mode", "")
//	fmt.Println(result.RawID)
func (m *MemoryNamespace) Add(ctx context.Context, endUserID, content, agentID string) (*AddResult, error) {
	body := map[string]interface{}{
		"end_user_id": endUserID,
		"content":     content,
	}
	if agentID != "" {
		body["agent_id"] = agentID
	}
	var out AddResult
	if err := m.http.post(ctx, "/v1/memory/add", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Get lists all active memories for a user, ordered by importance descending.
//
// Example:
//
//	result, err := g.Memory.Get(ctx, "user_123", gliaxin.GetMemoryOptions{})
//	for _, mem := range result.Memories {
//	    fmt.Println(mem.Category, mem.Content)
//	}
func (m *MemoryNamespace) Get(ctx context.Context, endUserID string, opts GetMemoryOptions) (*MemoryList, error) {
	page := opts.Page
	if page == 0 {
		page = 1
	}
	pageSize := opts.PageSize
	if pageSize == 0 {
		pageSize = 50
	}
	params := map[string]interface{}{
		"end_user_id": endUserID,
		"page":        page,
		"page_size":   pageSize,
	}
	if opts.Category != "" {
		params["category"] = opts.Category
	}
	if opts.MemoryType != "" {
		params["memory_type"] = opts.MemoryType
	}
	var out MemoryList
	if err := m.http.get(ctx, "/v1/memory/get", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Search performs semantic search over a user's memories using vector similarity.
// Returns memories ranked by relevance, with procedural memories pinned first.
//
// Example:
//
//	results, err := g.Memory.Search(ctx, "user_123", "language preferences", gliaxin.SearchMemoryOptions{Limit: 5})
//	for _, mem := range results {
//	    fmt.Println(mem.Content, mem.Importance)
//	}
func (m *MemoryNamespace) Search(ctx context.Context, endUserID, query string, opts SearchMemoryOptions) ([]Memory, error) {
	limit := opts.Limit
	if limit == 0 {
		limit = 10
	}
	params := map[string]interface{}{
		"end_user_id": endUserID,
		"query":       query,
		"limit":       limit,
	}
	if opts.AgentID != "" {
		params["agent_id"] = opts.AgentID
	}
	if opts.Category != "" {
		params["category"] = opts.Category
	}
	if opts.HasMinImportance {
		params["min_importance"] = opts.MinImportance
	}
	var out struct {
		Memories []Memory `json:"memories"`
	}
	if err := m.http.get(ctx, "/v1/memory/search", params, &out); err != nil {
		return nil, err
	}
	return out.Memories, nil
}

// Timeline returns full memory history including disputed and superseded entries,
// ordered chronologically. Useful for auditing or time-travel replay.
//
// Example:
//
//	history, err := g.Memory.Timeline(ctx, "user_123", gliaxin.TimelineOptions{})
//	for _, mem := range history.Memories {
//	    fmt.Println(mem.CreatedAt, mem.Status, mem.Content)
//	}
func (m *MemoryNamespace) Timeline(ctx context.Context, endUserID string, opts TimelineOptions) (*MemoryList, error) {
	page := opts.Page
	if page == 0 {
		page = 1
	}
	pageSize := opts.PageSize
	if pageSize == 0 {
		pageSize = 50
	}
	params := map[string]interface{}{
		"end_user_id": endUserID,
		"page":        page,
		"page_size":   pageSize,
	}
	var out MemoryList
	if err := m.http.get(ctx, "/v1/memory/timeline", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Forget permanently deletes all memories and the vault for a user.
// Irreversible. Use for GDPR right-to-erasure requests.
//
// Example:
//
//	result, err := g.Memory.Forget(ctx, "user_123")
//	fmt.Println(result.Deleted) // true
func (m *MemoryNamespace) Forget(ctx context.Context, endUserID string) (*ForgetResult, error) {
	var out ForgetResult
	if err := m.http.delete(ctx, "/v1/memory/forget", map[string]interface{}{
		"end_user_id": endUserID,
	}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Conflicts lists memory conflicts for a user.
//
// A conflict is created when two memories share the same slot
// (e.g. preferred_language). The new memory waits as "disputed"
// while the old stays "active".
//
// status must be "pending", "resolved", or "dismissed" (default "pending").
//
// Example:
//
//	result, err := g.Memory.Conflicts(ctx, "user_123", "pending")
//	for _, c := range result.Conflicts {
//	    fmt.Println(c.Slot, c.OldMemory, c.NewMemory)
//	}
func (m *MemoryNamespace) Conflicts(ctx context.Context, endUserID, status string) (*ConflictList, error) {
	if status == "" {
		status = "pending"
	}
	params := map[string]interface{}{
		"end_user_id": endUserID,
		"status":      status,
	}
	var out ConflictList
	if err := m.http.get(ctx, "/v1/memory/conflicts", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Resolve resolves a memory conflict.
//
// resolution must be "keep_old" or "keep_new".
//
// Example:
//
//	result, err := g.Memory.Resolve(ctx, "conflict-uuid", "keep_new")
//	fmt.Println(result.Winner)
func (m *MemoryNamespace) Resolve(ctx context.Context, conflictID, resolution string) (*ResolveResult, error) {
	if resolution != "keep_old" && resolution != "keep_new" {
		return nil, fmt.Errorf("gliaxin: resolution must be 'keep_old' or 'keep_new', got %q", resolution)
	}
	var out ResolveResult
	if err := m.http.post(ctx, "/v1/memory/resolve", map[string]interface{}{
		"conflict_id": conflictID,
		"resolution":  resolution,
	}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Raw reads Layer A verbatim records — the exact words the user said.
//
// No AI processing. Returns raw content + timestamps straight from the
// immutable store. Useful for debugging or when the agent needs the
// literal transcript rather than extracted facts.
// Pass limit=0 and page=0 to use defaults (page 1, 50 per page).
//
// Example:
//
//	result, err := g.Memory.Raw(ctx, "user_123", gliaxin.RawOptions{})
//	for _, r := range result.Records {
//	    fmt.Println(r.CreatedAt, r.Content)
//	}
func (m *MemoryNamespace) Raw(ctx context.Context, endUserID string, opts RawOptions) (*RawList, error) {
	page := opts.Page
	if page == 0 {
		page = 1
	}
	pageSize := opts.PageSize
	if pageSize == 0 {
		pageSize = 50
	}
	params := map[string]interface{}{
		"end_user_id": endUserID,
		"page":        page,
		"page_size":   pageSize,
	}
	if opts.AgentID != "" {
		params["agent_id"] = opts.AgentID
	}
	var out RawList
	if err := m.http.get(ctx, "/v1/memory/raw", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Fix reports a specific Layer B memory as wrong or inaccurate.
//
// Deletes the bad processed record and resets the linked raw Layer A
// entry to pending so the worker re-extracts it cleanly.
// Pass reason="" to skip the reason field.
//
// Example:
//
//	result, err := g.Memory.Fix(ctx, "mem-uuid", "Wrong category assigned")
//	fmt.Println(result.Queued)   // true
//	fmt.Println(result.RawID)    // the raw record that will be re-extracted
func (m *MemoryNamespace) Fix(ctx context.Context, memoryID, reason string) (*FixResult, error) {
	if memoryID == "" {
		return nil, fmt.Errorf("gliaxin: memory_id is required")
	}
	body := map[string]interface{}{"memory_id": memoryID}
	if reason != "" {
		body["reason"] = reason
	}
	var out FixResult
	if err := m.http.post(ctx, "/v1/memory/fix", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Reprocess re-runs Gemini extraction and embedding on all raw records for a user.
// Use when the extraction model is upgraded or to rebuild LayerB from scratch.
//
// Example:
//
//	result, err := g.Memory.Reprocess(ctx, "user_123")
//	fmt.Printf("%d records queued\n", result.Queued)
func (m *MemoryNamespace) Reprocess(ctx context.Context, endUserID string) (*ReprocessResult, error) {
	var out ReprocessResult
	if err := m.http.post(ctx, "/v1/memory/reprocess", map[string]interface{}{
		"end_user_id": endUserID,
	}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
