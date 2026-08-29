// Package client is a thin HTTP wrapper over the AgentForge API Gateway's
// public REST API (services/api-gateway) — the exact same contract the
// dashboard and Python SDK use. It never touches AgentForge's database or
// internal services directly; every request goes over the same
// X-API-Key-authenticated HTTPS surface any external caller would use.
package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type Client struct {
	BaseURL string
	APIKey  string
	http    *http.Client
}

func New(baseURL, apiKey string) *Client {
	return &Client{
		BaseURL: baseURL,
		APIKey:  apiKey,
		http:    &http.Client{Timeout: 60 * time.Second},
	}
}

// APIError mirrors the platform's {"error": {"code", "message"}} envelope
// (see agentforge_common.envelope.ErrorResponse) so callers can match on
// Code the same way the dashboard's ApiError does.
type APIError struct {
	Status  int
	Code    string
	Message string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("%s (%s): %s", http.StatusText(e.Status), e.Code, e.Message)
}

type errorEnvelope struct {
	Error struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

// do sends a request and decodes the response's top-level "data" field
// (dataResponse's shape) into out. Pass nil for out on a 204 response.
func (c *Client) do(method, path string, body any, out any) error {
	var reqBody io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("encoding request body: %w", err)
		}
		reqBody = bytes.NewReader(b)
	}

	req, err := http.NewRequest(method, c.BaseURL+path, reqBody)
	if err != nil {
		return fmt.Errorf("building request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("X-API-Key", c.APIKey)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("calling %s: %w", c.BaseURL+path, err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading response: %w", err)
	}

	if resp.StatusCode >= 400 {
		var envelope errorEnvelope
		_ = json.Unmarshal(respBody, &envelope) // best-effort; fall back to a generic message below
		if envelope.Error.Code == "" {
			envelope.Error.Code = "unknown_error"
			envelope.Error.Message = string(respBody)
		}
		return &APIError{Status: resp.StatusCode, Code: envelope.Error.Code, Message: envelope.Error.Message}
	}

	if out == nil || resp.StatusCode == http.StatusNoContent {
		return nil
	}

	var wrapper struct {
		Data json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(respBody, &wrapper); err != nil {
		return fmt.Errorf("parsing response envelope: %w", err)
	}
	if err := json.Unmarshal(wrapper.Data, out); err != nil {
		return fmt.Errorf("parsing response data: %w", err)
	}
	return nil
}

// --- Domain types (mirror agentforge_common.models / api-gateway routers) ---

type Agent struct {
	ID           string `json:"id"`
	Name         string `json:"name"`
	Model        string `json:"model"`
	SystemPrompt string `json:"system_prompt"`
	Status       string `json:"status"`
	CreatedAt    string `json:"created_at"`
}

type CreateAgentRequest struct {
	Name         string `json:"name"`
	Model        string `json:"model"`
	SystemPrompt string `json:"system_prompt"`
}

type RunRequest struct {
	Input string `json:"input"`
}

type Run struct {
	ID     string `json:"id"`
	Status string `json:"status"`
	Output string `json:"output"`
}

type EvalRun struct {
	ID      string `json:"id"`
	Status  string `json:"status"`
	Summary map[string]any `json:"summary"`
}

// --- Agents ---

func (c *Client) ListAgents() ([]Agent, error) {
	var agents []Agent
	if err := c.do(http.MethodGet, "/api/v1/agents?limit=100", nil, &agents); err != nil {
		return nil, err
	}
	return agents, nil
}

func (c *Client) GetAgent(id string) (Agent, error) {
	var agent Agent
	err := c.do(http.MethodGet, "/api/v1/agents/"+id, nil, &agent)
	return agent, err
}

func (c *Client) CreateAgent(req CreateAgentRequest) (Agent, error) {
	var agent Agent
	err := c.do(http.MethodPost, "/api/v1/agents", req, &agent)
	return agent, err
}

func (c *Client) RunAgent(agentID, input string) (Run, error) {
	var run Run
	err := c.do(http.MethodPost, "/api/v1/agents/"+agentID+"/run", RunRequest{Input: input}, &run)
	return run, err
}

// --- Evals ---

func (c *Client) RunEvalSuite(suiteID string) (EvalRun, error) {
	var evalRun EvalRun
	err := c.do(http.MethodPost, "/api/v1/eval-suites/"+suiteID+"/run", nil, &evalRun)
	return evalRun, err
}

// --- Health (used by `login` to verify the URL/key actually work) ---

func (c *Client) Ping() error {
	return c.do(http.MethodGet, "/api/v1/agents?limit=1", nil, &[]Agent{})
}
