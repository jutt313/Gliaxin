package gliaxin

import (
	"context"
	"fmt"
)

// AgentNamespace groups all /v1/agent/* operations.
// Access via client.Agent.
type AgentNamespace struct {
	http *httpClient
}

// Register creates a named agent within your project.
//
// Idempotent — registering the same name returns the existing agent
// without creating a duplicate. Registered is true if newly created,
// false if already existed.
//
// Example:
//
//	agent, err := g.Agent.Register(ctx, "support-bot")
//	fmt.Println(agent.AgentID, agent.Registered)
func (a *AgentNamespace) Register(ctx context.Context, name string) (*RegisterResult, error) {
	var out RegisterResult
	if err := a.http.post(ctx, "/v1/agent/register", map[string]interface{}{"name": name}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// List returns all active agents in your project.
//
// Example:
//
//	result, err := g.Agent.List(ctx)
//	for _, a := range result.Agents {
//	    fmt.Println(a.Name, a.AgentID)
//	}
func (a *AgentNamespace) List(ctx context.Context) (*AgentList, error) {
	var out AgentList
	if err := a.http.get(ctx, "/v1/agent/list", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Delete soft-deletes an agent. The agent will no longer appear in
// List or Register responses.
//
// Example:
//
//	result, err := g.Agent.Delete(ctx, "agent-uuid")
//	fmt.Println(result.Deleted) // true
func (a *AgentNamespace) Delete(ctx context.Context, agentID string) (*DeleteResult, error) {
	var out DeleteResult
	if err := a.http.delete(ctx, fmt.Sprintf("/v1/agent/%s", agentID), nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Shared returns all project-scoped active memories for a user, visible to
// every agent in the project. Sorted by importance — procedural memories first.
//
// Use this at the start of an agent turn to load shared user context.
// Pass limit=0 to use the default of 50.
//
// Example:
//
//	ctx, err := g.Agent.Shared(ctx, "user_123", 0)
//	for _, mem := range ctx.Memories {
//	    fmt.Printf("[%s] %s\n", mem.Category, mem.Content)
//	}
func (a *AgentNamespace) Shared(ctx context.Context, endUserID string, limit int) (*MemoryList, error) {
	if limit == 0 {
		limit = 50
	}
	params := map[string]interface{}{
		"end_user_id": endUserID,
		"limit":       limit,
	}
	var out MemoryList
	if err := a.http.get(ctx, "/v1/agent/shared", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
