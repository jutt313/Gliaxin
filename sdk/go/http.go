package gliaxin

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

type httpClient struct {
	apiKey  string
	baseURL string
	client  *http.Client
}

func newHTTPClient(apiKey, baseURL string, timeout time.Duration) *httpClient {
	return &httpClient{
		apiKey:  apiKey,
		baseURL: baseURL,
		client:  &http.Client{Timeout: timeout},
	}
}

func (h *httpClient) do(
	ctx context.Context,
	method, path string,
	params map[string]interface{},
	body map[string]interface{},
	out interface{},
) error {
	u, err := url.Parse(h.baseURL + path)
	if err != nil {
		return fmt.Errorf("gliaxin: invalid URL: %w", err)
	}

	if method == http.MethodGet && params != nil {
		q := u.Query()
		for k, v := range params {
			if v == nil {
				continue
			}
			switch val := v.(type) {
			case string:
				if val != "" {
					q.Set(k, val)
				}
			case int:
				q.Set(k, strconv.Itoa(val))
			case float64:
				q.Set(k, strconv.FormatFloat(val, 'f', -1, 64))
			case bool:
				q.Set(k, strconv.FormatBool(val))
			}
		}
		u.RawQuery = q.Encode()
	}

	var bodyReader io.Reader
	if body != nil && method != http.MethodGet {
		b, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("gliaxin: marshal request: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequestWithContext(ctx, method, u.String(), bodyReader)
	if err != nil {
		return fmt.Errorf("gliaxin: create request: %w", err)
	}

	req.Header.Set("X-Api-Key", h.apiKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := h.client.Do(req)
	if err != nil {
		return fmt.Errorf("gliaxin: request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("gliaxin: read response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var errBody struct {
			Detail string `json:"detail"`
		}
		if jsonErr := json.Unmarshal(respBody, &errBody); jsonErr != nil || errBody.Detail == "" {
			errBody.Detail = fmt.Sprintf("HTTP %d", resp.StatusCode)
		}
		return newAPIError(resp.StatusCode, errBody.Detail)
	}

	if out != nil {
		if err := json.Unmarshal(respBody, out); err != nil {
			return fmt.Errorf("gliaxin: decode response: %w", err)
		}
	}
	return nil
}

func (h *httpClient) get(ctx context.Context, path string, params map[string]interface{}, out interface{}) error {
	return h.do(ctx, http.MethodGet, path, params, nil, out)
}

func (h *httpClient) post(ctx context.Context, path string, body map[string]interface{}, out interface{}) error {
	return h.do(ctx, http.MethodPost, path, nil, body, out)
}

func (h *httpClient) delete(ctx context.Context, path string, body map[string]interface{}, out interface{}) error {
	return h.do(ctx, http.MethodDelete, path, nil, body, out)
}
