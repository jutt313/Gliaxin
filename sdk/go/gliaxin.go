// Package gliaxin is the official Go SDK for the Gliaxin memory API.
//
// Gliaxin is a persistent, structured memory layer for AI agents. It stores
// raw inputs forever (LayerA) and rebuilds structured memory (LayerB) whenever
// the extraction model improves — no migrations, no data loss.
//
// Install:
//
//	go get github.com/gliaxin/sdk
//
// Quick start:
//
//	import "github.com/gliaxin/sdk"
//
//	g, err := gliaxin.New("glx_YOUR_KEY")
//	if err != nil {
//	    log.Fatal(err)
//	}
//
//	ctx := context.Background()
//
//	// Save a memory
//	result, err := g.Memory.Add(ctx, "user_123", "User prefers TypeScript", "")
//
//	// Search memories
//	memories, err := g.Memory.Search(ctx, "user_123", "language preferences",
//	    gliaxin.SearchMemoryOptions{Limit: 5})
//
//	// One-line LLM wrapper with automatic memory injection
//	wrapper := g.Wrap(myLLMFunc, gliaxin.WrapOptions{})
//	reply, err := wrapper.Chat(ctx, "user_123", "What do I like?", gliaxin.ChatOptions{})
package gliaxin

import (
	"errors"
	"strings"
	"time"
)

const defaultBaseURL = "https://api.gliaxin.com"

// Client is the Gliaxin API client.
// Create one with New.
type Client struct {
	Memory *MemoryNamespace
	Agent  *AgentNamespace
	http   *httpClient
}

// New creates a new Gliaxin client.
//
// apiKey must start with "glx_". Use WithBaseURL or WithTimeout to customise
// the HTTP behaviour.
//
// Example:
//
//	g, err := gliaxin.New("glx_YOUR_KEY")
//	g, err := gliaxin.New("glx_YOUR_KEY", gliaxin.WithTimeout(10*time.Second))
func New(apiKey string, opts ...Option) (*Client, error) {
	if !strings.HasPrefix(apiKey, "glx_") {
		return nil, errors.New("gliaxin: api_key must start with 'glx_'")
	}

	cfg := config{
		baseURL: defaultBaseURL,
		timeout: 30 * time.Second,
	}
	for _, o := range opts {
		o(&cfg)
	}

	h := newHTTPClient(apiKey, cfg.baseURL, cfg.timeout)
	return &Client{
		Memory: &MemoryNamespace{http: h},
		Agent:  &AgentNamespace{http: h},
		http:   h,
	}, nil
}

// Wrap wraps any LLMFunc with automatic turn-based memory.
//
// On every Wrapper.Chat call:
//  1. Registers the agent by name (idempotent, cached after first call).
//  2. Searches the user's memories using that agent's identity.
//  3. Injects found memories into the system prompt.
//  4. Calls your LLM.
//  5. Saves the full turn (user + assistant) attributed to the agent.
//
// WrapOptions.AgentName is required.
//
// Example:
//
//	myLLM := func(ctx context.Context, messages []gliaxin.Message) (string, error) {
//	    return callOpenAI(ctx, messages)
//	}
//
//	wrapper := g.Wrap(myLLM, gliaxin.WrapOptions{AgentName: "support-bot"})
//	reply, err := wrapper.Chat(ctx, "user_123", "What do I like?", gliaxin.ChatOptions{})
func (c *Client) Wrap(llm LLMFunc, opts WrapOptions) *Wrapper {
	return &Wrapper{g: c, llm: llm, opts: opts}
}

// Option is a functional option for New.
type Option func(*config)

type config struct {
	baseURL string
	timeout time.Duration
}

// WithBaseURL overrides the API base URL.
// Useful for self-hosting or local testing.
func WithBaseURL(u string) Option {
	return func(c *config) { c.baseURL = strings.TrimRight(u, "/") }
}

// WithTimeout sets the HTTP request timeout (default 30s).
func WithTimeout(d time.Duration) Option {
	return func(c *config) { c.timeout = d }
}
