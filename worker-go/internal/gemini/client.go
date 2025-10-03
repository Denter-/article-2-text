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
	// For now, return a placeholder description
	// Full Gemini Vision integration will be added in Python worker
	// which already has the working implementation

	return fmt.Sprintf("Image from article (URL: %s)\n\nNote: Full AI-powered image descriptions are available through the Python worker, which uses the complete Gemini Vision API with proper image analysis. This Go worker provides fast extraction for sites with learned configurations.", imageURL), nil
}
