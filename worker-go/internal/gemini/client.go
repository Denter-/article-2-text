package gemini

import (
	"context"
	"fmt"

	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/option"
)

type Client struct {
	model *genai.GenerativeModel
}

func NewClient(apiKey string) (*Client, error) {
	ctx := context.Background()
	client, err := genai.NewClient(ctx, option.WithAPIKey(apiKey))
	if err != nil {
		return nil, fmt.Errorf("failed to create Gemini client: %w", err)
	}

	model := client.GenerativeModel("gemini-2.0-flash-exp")
	model.SetTemperature(0.4)

	return &Client{
		model: model,
	}, nil
}

func (c *Client) DescribeImage(ctx context.Context, imageURL string) (string, error) {
	// For now, implement a simple approach - this can be enhanced later
	// to download and process images with Gemini Vision

	// Use Gemini to generate a description based on the URL context
	prompt := fmt.Sprintf(`Provide a description for an image from this URL: %s

This image is from an article about SaaS metrics and business concepts.
Given the URL context, provide a likely description of what this image might contain,
focusing on business charts, metrics, diagrams, or SaaS-related concepts that would
typically be found in such articles.`, imageURL)

	resp, err := c.model.GenerateContent(ctx, genai.Text(prompt))
	if err != nil {
		return "", fmt.Errorf("failed to generate content: %w", err)
	}

	if len(resp.Candidates) == 0 {
		return "", fmt.Errorf("no response generated")
	}

	description := resp.Candidates[0].Content.Parts[0].(genai.Text)
	return string(description), nil
}
