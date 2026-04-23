package gliaxin

import (
	"context"
	"fmt"
	"strings"
	"sync"
)

// LLMFunc is any function that accepts a list of messages and returns a reply.
// Works with OpenAI, Anthropic, Gemini, Ollama, LiteLLM — anything that
// takes a []Message and returns (string, error).
type LLMFunc func(ctx context.Context, messages []Message) (string, error)

// WrapOptions configures a Wrapper returned by Client.Wrap.
type WrapOptions struct {
	// AgentName is required. Human-readable name for the agent.
	// Auto-registered on first Chat call (idempotent).
	AgentName string
	// Scope controls memory visibility for saved turns.
	// "agent" = private to this agent (default).
	// "project" = shared across all agents in the project.
	Scope string
	// ContextLimit is the max memories injected per call (default 10).
	ContextLimit int
	// DisableAutoRegister skips agent registration on first call.
	// By default auto-register is ON.
	DisableAutoRegister bool
	// DisableAutoSave disables automatic saving of the full turn after each call.
	// By default auto-save is ON.
	DisableAutoSave bool
	// SystemPrefix is prepended before the memory block in the system prompt.
	// Defaults to "You have access to the following memories about this user:".
	// Set to a single space " " to suppress the header while keeping memories.
	SystemPrefix string
}

// ChatOptions are per-call options for Wrapper.Chat.
type ChatOptions struct {
	// History is optional prior conversation turns.
	History []Message
	// System is an optional base system prompt.
	// Retrieved memories are appended to it automatically.
	System string
}

// Wrapper wraps any LLMFunc with automatic turn-based memory.
// Create one via Client.Wrap.
type Wrapper struct {
	g       *Client
	llm     LLMFunc
	opts    WrapOptions
	agentID string
	mu      sync.Mutex
}

// Chat sends a message with automatic memory injection and full-turn auto-save.
//
// On every call:
//  1. Ensures the agent is registered (idempotent, cached after first call).
//  2. Searches the user's memories using that agent's identity.
//  3. Injects found memories silently into the system prompt.
//  4. Calls your LLM with the enriched message list.
//  5. Saves the full turn (user + assistant) attributed to the agent.
//
// Example:
//
//	reply, err := wrapper.Chat(ctx, "user_123", "What do I like?", gliaxin.ChatOptions{})
func (w *Wrapper) Chat(ctx context.Context, userID, message string, opts ChatOptions) (string, error) {
	agentID, err := w.ensureRegistered(ctx)
	if err != nil {
		return "", fmt.Errorf("gliaxin wrap: agent registration: %w", err)
	}

	limit := w.opts.ContextLimit
	if limit == 0 {
		limit = 10
	}

	scope := w.opts.Scope
	if scope == "" {
		scope = "agent"
	}

	memories, err := w.g.Memory.Search(ctx, userID, message, SearchMemoryOptions{
		Limit:   limit,
		AgentID: agentID,
	})
	if err != nil {
		return "", fmt.Errorf("gliaxin wrap: memory search: %w", err)
	}

	messages := buildMessages(message, memories, opts.History, opts.System, w.opts.SystemPrefix)

	reply, err := w.llm(ctx, messages)
	if err != nil {
		return "", err
	}

	if !w.opts.DisableAutoSave && agentID != "" {
		// Best-effort — save errors never break the caller's response flow.
		_, _ = w.g.Memory.AddTurn(ctx, userID, agentID, []Message{
			{Role: "user",      Content: message},
			{Role: "assistant", Content: reply},
		}, AddTurnOptions{Scope: scope})
	}

	return reply, nil
}

func (w *Wrapper) ensureRegistered(ctx context.Context) (string, error) {
	if w.opts.DisableAutoRegister {
		w.mu.Lock()
		id := w.agentID
		w.mu.Unlock()
		return id, nil
	}
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.agentID != "" {
		return w.agentID, nil
	}
	result, err := w.g.Agent.Register(ctx, w.opts.AgentName)
	if err != nil {
		return "", err
	}
	w.agentID = result.AgentID
	return w.agentID, nil
}

func buildMessages(message string, memories []Memory, history []Message, system, prefix string) []Message {
	var msgs []Message

	var sysParts []string
	if system != "" {
		sysParts = append(sysParts, system)
	}

	if len(memories) > 0 {
		var lines []string
		header := prefix
		if header == "" {
			header = "You have access to the following memories about this user:"
		}
		if strings.TrimSpace(header) != "" {
			lines = append(lines, header)
		}
		for _, mem := range memories {
			lines = append(lines, fmt.Sprintf("- [%s] %s", mem.Category, mem.Content))
		}
		sysParts = append(sysParts, strings.Join(lines, "\n"))
	}

	if len(sysParts) > 0 {
		msgs = append(msgs, Message{
			Role:    "system",
			Content: strings.Join(sysParts, "\n\n"),
		})
	}

	msgs = append(msgs, history...)
	msgs = append(msgs, Message{Role: "user", Content: message})
	return msgs
}
