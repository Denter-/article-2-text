package extractor

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
	"gopkg.in/yaml.v3"

	"github.com/Denter-/article-extraction/worker/internal/gemini"
	"github.com/Denter-/article-extraction/worker/internal/repository"
)

type Extractor struct {
	httpClient   *http.Client
	geminiClient *gemini.Client
	storagePath  string
	configDir    string
}

type ExtractionResult struct {
	Path       string
	Markdown   string
	Title      string
	Author     string
	WordCount  int
	ImageCount int
}

type Image struct {
	URL string
	Alt string
}

type ImageDescription struct {
	URL         string
	Alt         string
	Description string
}

// SiteConfig represents the YAML site configuration
type SiteConfig struct {
	Domain     string `yaml:"domain"`
	LearnedAt  string `yaml:"learned_at"`
	Extraction struct {
		ArticleContent struct {
			Selector         string   `yaml:"selector"`
			Fallback         string   `yaml:"fallback"`
			ExcludeSelectors []string `yaml:"exclude_selectors"`
			CleanupRules     struct {
				StopAtRepeatedLinks bool     `yaml:"stop_at_repeated_links"`
				MaxConsecutiveLinks int      `yaml:"max_consecutive_links"`
				RemovePatterns      []string `yaml:"remove_patterns"`
			} `yaml:"cleanup_rules"`
		} `yaml:"article_content"`
		Title struct {
			OGMeta           string `yaml:"og_meta"`
			FallbackSelector string `yaml:"fallback_selector"`
		} `yaml:"title"`
		Author struct {
			FallbackSelector string `yaml:"fallback_selector"`
			FallbackMeta     string `yaml:"fallback_meta"`
		} `yaml:"author"`
		ContentPattern struct {
			StartMarker string `yaml:"start_marker"`
			EndMarker   string `yaml:"end_marker"`
		} `yaml:"content_pattern"`
	} `yaml:"extraction"`
	Notes string `yaml:"notes"`
}

func New(geminiClient *gemini.Client, storagePath, configDir string) *Extractor {
	return &Extractor{
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		geminiClient: geminiClient,
		storagePath:  storagePath,
		configDir:    configDir,
	}
}

func (e *Extractor) Extract(ctx context.Context, job *repository.Job, dbConfig *repository.SiteConfig) (*ExtractionResult, error) {
	log.Info().
		Str("job_id", job.ID.String()).
		Str("url", job.URL).
		Msg("Starting extraction")

	// Fetch HTML
	html, err := e.fetchHTML(job.URL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch HTML: %w", err)
	}

	// Parse HTML
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Parse site config from database
	var config *SiteConfig
	if dbConfig != nil && dbConfig.ConfigYAML != "" {
		config = &SiteConfig{}
		if err := yaml.Unmarshal([]byte(dbConfig.ConfigYAML), config); err != nil {
			log.Warn().Err(err).Str("domain", job.Domain).Msg("Failed to parse site config from database")
			config = nil
		} else {
			log.Info().Str("domain", job.Domain).Msg("✓ Loaded site config from database")
		}
	}

	// Extract article content with config
	var articleHTML string
	var title, author string

	if config != nil {
		title = e.extractTitleWithConfig(doc, config)
		author = e.extractAuthorWithConfig(doc, config)
		articleHTML = e.extractContentWithConfig(doc, config, html)
	} else {
		title = e.extractTitle(doc)
		author = e.extractAuthor(doc)
		articleHTML = e.extractContentFallback(doc)
	}

	if articleHTML == "" {
		return nil, fmt.Errorf("failed to extract article content")
	}

	// Parse cleaned HTML for further processing
	articleDoc, err := goquery.NewDocumentFromReader(strings.NewReader(articleHTML))
	if err != nil {
		return nil, fmt.Errorf("failed to parse article HTML: %w", err)
	}

	// Extract images from cleaned content
	images := e.extractImages(articleDoc, job.URL)
	log.Info().
		Str("job_id", job.ID.String()).
		Int("image_count", len(images)).
		Msg("Extracted images")

	// Process images in parallel
	descriptions := e.processImagesParallel(ctx, images)

	// Clean HTML before markdown conversion
	articleDoc = e.cleanHTML(articleDoc)

	// Convert HTML to Markdown
	markdown := e.htmlToMarkdown(articleDoc, title, author, descriptions)

	// Save result
	path, err := e.saveResult(job.ID, title, markdown)
	if err != nil {
		return nil, fmt.Errorf("failed to save result: %w", err)
	}

	return &ExtractionResult{
		Path:       path,
		Markdown:   markdown,
		Title:      title,
		Author:     author,
		WordCount:  len(strings.Fields(markdown)),
		ImageCount: len(images),
	}, nil
}

func (e *Extractor) getDomainFromURL(urlStr string) (string, error) {
	parsed, err := url.Parse(urlStr)
	if err != nil {
		return "", err
	}
	domain := parsed.Hostname()
	domain = strings.TrimPrefix(domain, "www.")
	return domain, nil
}

func (e *Extractor) loadSiteConfig(domain string) (*SiteConfig, error) {
	configPath := filepath.Join(e.configDir, fmt.Sprintf("%s.yaml", domain))

	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}

	var config SiteConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	log.Info().Str("domain", domain).Msg("✓ Loaded site config")
	log.Debug().Str("start_marker", config.Extraction.ContentPattern.StartMarker).Str("end_marker", config.Extraction.ContentPattern.EndMarker).Msg("Pattern config loaded")
	return &config, nil
}

func (e *Extractor) ForwardToPythonAIWorker(ctx context.Context, job *repository.Job) (*ExtractionResult, error) {
	log.Info().Str("job_id", job.ID.String()).Str("url", job.URL).Msg("Forwarding to Python AI worker for learning")

	// Call Python AI worker
	client := &http.Client{Timeout: 5 * time.Minute}
	reqBody := map[string]string{
		"job_id": job.ID.String(),
		"url":    job.URL,
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := client.Post("http://localhost:8081/learn", "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to call Python AI worker: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Python AI worker failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Parse the response to get the actual results
	var response struct {
		Success bool   `json:"success"`
		Message string `json:"message"`
		Error   string `json:"error,omitempty"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode Python AI worker response: %w", err)
	}

	if !response.Success {
		return nil, fmt.Errorf("Python AI worker failed: %s", response.Error)
	}

	// The Python AI worker has completed the job and updated the database
	// We need to fetch the final job data from the database to get the actual results
	// For now, return a success indicator - the job is already completed in the database
	log.Info().Str("job_id", job.ID.String()).Msg("Python AI worker completed job successfully")

	return &ExtractionResult{
		Path:       "completed-by-python-ai-worker",
		Markdown:   "Content extracted by Python AI worker",
		Title:      "AI Learning Completed",
		Author:     "",
		WordCount:  0,
		ImageCount: 0,
	}, nil
}

func (e *Extractor) extractContentWithConfig(doc *goquery.Document, config *SiteConfig, rawHTML string) string {
	articleConfig := config.Extraction.ArticleContent

	// Use only site-specific exclusions from config
	excludeSelectors := articleConfig.ExcludeSelectors
	if len(excludeSelectors) == 0 {
		log.Info().Msg("No exclusions in config, using raw content")
	}

	// Try primary selector
	if articleConfig.Selector != "" {
		sel := doc.Find(articleConfig.Selector).First()
		if sel.Length() > 0 {
			log.Debug().Str("selector", articleConfig.Selector).Int("length", sel.Length()).Msg("Primary selector matched")
			content := e.applyExclusions(sel, excludeSelectors)
			log.Debug().Int("content_length", len(content)).Msg("After exclusions")
			if len(content) > 100 {
				return content
			}
			log.Warn().Str("selector", articleConfig.Selector).Msg("Primary selector content too short after exclusions")
		} else {
			log.Debug().Str("selector", articleConfig.Selector).Msg("Primary selector did not match")
		}
	}

	// Try fallback
	if articleConfig.Fallback != "" {
		sel := doc.Find(articleConfig.Fallback).First()
		if sel.Length() > 0 {
			log.Debug().Str("selector", articleConfig.Fallback).Int("length", sel.Length()).Msg("Fallback selector matched")
			content := e.applyExclusions(sel, excludeSelectors)
			log.Debug().Int("content_length", len(content)).Msg("After exclusions")
			if len(content) > 100 {
				return content
			}
			log.Warn().Str("selector", articleConfig.Fallback).Msg("Fallback selector content too short after exclusions")
		} else {
			log.Debug().Str("selector", articleConfig.Fallback).Msg("Fallback selector did not match")
		}
	}

	// Try pattern-based extraction if defined
	log.Debug().Str("start_marker", config.Extraction.ContentPattern.StartMarker).Str("end_marker", config.Extraction.ContentPattern.EndMarker).Msg("Checking pattern config")
	if config.Extraction.ContentPattern.StartMarker != "" && config.Extraction.ContentPattern.EndMarker != "" {
		log.Debug().Str("domain", config.Domain).Msg("Trying pattern-based extraction")
		patternContent := e.extractContentWithPattern(rawHTML, config.Extraction.ContentPattern)
		if patternContent != "" {
			// Parse the pattern content and apply exclusions
			patternDoc, err := goquery.NewDocumentFromReader(strings.NewReader(patternContent))
			if err == nil {
				body := patternDoc.Find("body").First()
				if body.Length() > 0 {
					return e.applyExclusions(body, excludeSelectors)
				}
			}
			// If parsing fails, return raw pattern content
			return patternContent
		}
	}

	// Use generic fallback
	log.Warn().Msg("Config selectors didn't match, using fallback")
	return e.extractContentFallback(doc)
}

func (e *Extractor) extractContentWithPattern(htmlContent string, pattern struct {
	StartMarker string `yaml:"start_marker"`
	EndMarker   string `yaml:"end_marker"`
}) string {
	startMarker := pattern.StartMarker
	endMarker := pattern.EndMarker

	if startMarker == "" || endMarker == "" {
		return ""
	}

	// Convert Perl-style lookahead to Go-compatible regex
	// Replace (?=...) with simple string matching
	goEndMarker := endMarker
	if strings.HasPrefix(endMarker, "(?=") && strings.HasSuffix(endMarker, ")") {
		// Extract the lookahead content
		lookahead := endMarker[3 : len(endMarker)-1]
		// For now, just use the first part before the | as the end marker
		if pipeIndex := strings.Index(lookahead, "|"); pipeIndex != -1 {
			goEndMarker = lookahead[:pipeIndex]
		} else {
			goEndMarker = lookahead
		}
		log.Debug().Str("original", endMarker).Str("converted", goEndMarker).Msg("Converted lookahead pattern")
	}

	// Try a much simpler approach: just look for content between h1 and footer
	if goEndMarker == "<footer" {
		// Use a very simple pattern - everything between h1 and footer
		startMarker = "<h1"
		goEndMarker = "<footer"
		log.Debug().Str("simplified_start", startMarker).Str("simplified_end", goEndMarker).Msg("Using simplified pattern")
	}

	// Compile regex pattern - make it more flexible
	patternStr := startMarker + "(.*?)" + goEndMarker
	log.Debug().Str("final_pattern", patternStr).Msg("Using final pattern")
	re, err := regexp.Compile("(?i)" + patternStr)
	if err != nil {
		log.Warn().Err(err).Str("pattern", patternStr).Msg("Failed to compile pattern")
		return ""
	}

	// Find match
	matches := re.FindStringSubmatch(htmlContent)
	if len(matches) < 2 {
		log.Debug().Str("pattern", patternStr).Msg("Pattern did not match")
		// Debug: check if start marker exists
		if strings.Contains(htmlContent, "<h1") || strings.Contains(htmlContent, "<h2") {
			log.Debug().Msg("Found h1/h2 tags in HTML")
		}
		if strings.Contains(htmlContent, "<footer") {
			log.Debug().Msg("Found footer tag in HTML")
		}
		return ""
	}

	content := matches[1]
	log.Debug().Str("pattern", patternStr).Int("length", len(content)).Msg("Pattern matched")
	return content
}

func (e *Extractor) applyExclusions(sel *goquery.Selection, excludeSelectors []string) string {
	// Clone the selection
	html, _ := sel.Html()

	// Validate input HTML
	if len(html) < 100 {
		log.Warn().Int("content_length", len(html)).Msg("Input content very short before exclusions")
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader("<div>" + html + "</div>"))
	if err != nil {
		log.Error().Err(err).Msg("Failed to parse HTML for exclusions")
		return html
	}

	root := doc.Find("div")

	// Use comprehensive default exclusions if none specified
	if len(excludeSelectors) == 0 {
		excludeSelectors = DefaultExclusions
		log.Info().Int("default_rules", len(DefaultExclusions)).Msg("Using default exclusion rules")
	}

	// Log before exclusions
	beforeText := strings.TrimSpace(root.Text())
	beforeWords := len(strings.Fields(beforeText))
	log.Debug().
		Int("html_length", len(html)).
		Int("text_length", len(beforeText)).
		Int("word_count", beforeWords).
		Msg("Content metrics before exclusions")

	// Remove excluded elements with detailed logging
	totalRemoved := 0
	removedByType := make(map[string]int)

	for _, selector := range excludeSelectors {
		found := root.Find(selector)
		count := found.Length()
		if count > 0 {
			// Log what we're removing for debugging
			if selector == ".elementor-widget-container" || selector == ".elementor-widget-theme-post-content" {
				// Be extra careful with content-containing selectors
				foundText := strings.TrimSpace(found.Text())
				foundWords := len(strings.Fields(foundText))
				log.Warn().
					Str("selector", selector).
					Int("removed", count).
					Int("removed_words", foundWords).
					Msg("Removing content-containing selector - potential data loss")
			} else {
				log.Debug().
					Str("selector", selector).
					Int("removed", count).
					Msg("Removed elements")
			}

			found.Remove()
			totalRemoved += count
			removedByType[selector] = count
		}
	}

	// Log after exclusions
	afterText := strings.TrimSpace(root.Text())
	afterWords := len(strings.Fields(afterText))
	contentLossRatio := float64(beforeWords-afterWords) / float64(beforeWords) * 100

	log.Info().
		Int("total_removed", totalRemoved).
		Int("exclusion_rules", len(excludeSelectors)).
		Int("words_before", beforeWords).
		Int("words_after", afterWords).
		Float64("content_loss_percent", contentLossRatio).
		Msg("Applied exclusions")

	// Alert if we lost too much content
	if contentLossRatio > 90 && beforeWords > 1000 {
		log.Error().
			Float64("content_loss_percent", contentLossRatio).
			Int("words_before", beforeWords).
			Int("words_after", afterWords).
			Msg("CRITICAL: High content loss detected during exclusions")
	}

	// Get the cleaned HTML
	cleanedHTML, _ := root.Html()

	// Validate output
	if len(strings.TrimSpace(cleanedHTML)) < 100 {
		log.Warn().
			Int("cleaned_length", len(cleanedHTML)).
			Msg("Cleaned content very short after exclusions")
	}

	return cleanedHTML
}

func (e *Extractor) extractContentFallback(doc *goquery.Document) string {
	selectors := []string{
		"article",
		"main article",
		".article-content",
		".post-content",
		".entry-content",
		"[role='main']",
		"main",
	}

	for _, selector := range selectors {
		sel := doc.Find(selector).First()
		if sel.Length() > 0 {
			log.Debug().Str("selector", selector).Msg("Using fallback selector")
			html, _ := sel.Html()
			return html
		}
	}

	// Last resort - use body without exclusions
	log.Warn().Msg("Using body as last resort")
	body := doc.Find("body").First()
	html, _ := body.Html()
	return html
}

func (e *Extractor) extractTitleWithConfig(doc *goquery.Document, config *SiteConfig) string {
	titleConfig := config.Extraction.Title

	// Try OG meta
	if titleConfig.OGMeta != "" {
		if title, exists := doc.Find(fmt.Sprintf("meta[property='%s']", titleConfig.OGMeta)).Attr("content"); exists && title != "" {
			return title
		}
	}

	// Try fallback selector
	if titleConfig.FallbackSelector != "" {
		if title := doc.Find(titleConfig.FallbackSelector).First().Text(); title != "" {
			return strings.TrimSpace(title)
		}
	}

	return e.extractTitle(doc)
}

func (e *Extractor) extractAuthorWithConfig(doc *goquery.Document, config *SiteConfig) string {
	authorConfig := config.Extraction.Author

	// Try fallback selector
	if authorConfig.FallbackSelector != "" {
		if author := doc.Find(authorConfig.FallbackSelector).First().Text(); author != "" {
			return strings.TrimSpace(author)
		}
	}

	return e.extractAuthor(doc)
}

func (e *Extractor) fetchHTML(urlStr string) (string, error) {
	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		return "", err
	}

	// Add headers to bypass Cloudflare protection
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")
	req.Header.Set("Accept-Encoding", "gzip, deflate")
	req.Header.Set("Connection", "keep-alive")
	req.Header.Set("Upgrade-Insecure-Requests", "1")

	resp, err := e.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(body), nil
}

func (e *Extractor) extractTitle(doc *goquery.Document) string {
	// Try meta tags first
	if title, exists := doc.Find("meta[property='og:title']").Attr("content"); exists && title != "" {
		return title
	}

	// Try h1
	if title := doc.Find("h1").First().Text(); title != "" {
		return strings.TrimSpace(title)
	}

	// Fallback to title tag
	return strings.TrimSpace(doc.Find("title").Text())
}

func (e *Extractor) extractAuthor(doc *goquery.Document) string {
	// Try meta tags
	if author, exists := doc.Find("meta[name='author']").Attr("content"); exists && author != "" {
		return author
	}

	if author, exists := doc.Find("meta[property='article:author']").Attr("content"); exists && author != "" {
		return author
	}

	// Try common author selectors
	if author := doc.Find(".author, .author-name, [rel='author']").First().Text(); author != "" {
		return strings.TrimSpace(author)
	}

	return ""
}

func (e *Extractor) extractImages(doc *goquery.Document, baseURL string) []Image {
	var images []Image
	seen := make(map[string]bool)

	doc.Find("img").Each(func(i int, s *goquery.Selection) {
		src, exists := s.Attr("src")
		if !exists || src == "" {
			return
		}

		// Resolve relative URLs
		imgURL, err := e.resolveURL(baseURL, src)
		if err != nil {
			return
		}

		// Skip if already seen
		if seen[imgURL] {
			return
		}
		seen[imgURL] = true

		// Skip small images (likely icons/logos)
		if width, exists := s.Attr("width"); exists {
			var w int
			fmt.Sscanf(width, "%d", &w)
			if w < 100 {
				return
			}
		}

		alt, _ := s.Attr("alt")

		images = append(images, Image{
			URL: imgURL,
			Alt: alt,
		})
	})

	return images
}

func (e *Extractor) resolveURL(base, href string) (string, error) {
	baseURL, err := url.Parse(base)
	if err != nil {
		return "", err
	}

	hrefURL, err := url.Parse(href)
	if err != nil {
		return "", err
	}

	return baseURL.ResolveReference(hrefURL).String(), nil
}

func (e *Extractor) processImagesParallel(ctx context.Context, images []Image) []ImageDescription {
	descriptions := make([]ImageDescription, len(images))
	var wg sync.WaitGroup

	// Limit concurrency to avoid rate limits
	semaphore := make(chan struct{}, 5)

	for i, img := range images {
		wg.Add(1)
		go func(idx int, image Image) {
			defer wg.Done()

			// Acquire semaphore
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			// Add small delay to avoid rate limiting
			time.Sleep(time.Duration(idx) * 100 * time.Millisecond)

			desc, err := e.geminiClient.DescribeImage(ctx, image.URL)
			if err != nil {
				log.Warn().
					Err(err).
					Str("url", image.URL).
					Msg("Failed to describe image")
				desc = fmt.Sprintf("Image: %s (Description unavailable)", image.Alt)
			}

			descriptions[idx] = ImageDescription{
				URL:         image.URL,
				Alt:         image.Alt,
				Description: desc,
			}

			log.Debug().
				Int("image", idx+1).
				Int("total", len(images)).
				Msg("Processed image")
		}(i, img)
	}

	wg.Wait()
	return descriptions
}

// HtmlToMarkdown is a public wrapper for htmlToMarkdown
func (e *Extractor) HtmlToMarkdown(doc *goquery.Document, title, author string, images []ImageDescription) string {
	return e.htmlToMarkdown(doc, title, author, images)
}

func (e *Extractor) htmlToMarkdown(doc *goquery.Document, title, author string, images []ImageDescription) string {
	var md strings.Builder

	// Title
	md.WriteString("# ")
	md.WriteString(title)
	md.WriteString("\n\n")

	// Author
	if author != "" {
		md.WriteString("**Author:** ")
		md.WriteString(author)
		md.WriteString("\n\n")
	}

	md.WriteString("---\n\n")

	// Enhanced content detection and validation
	bodyContent := e.extractContentFromDocument(doc)
	if bodyContent == nil || bodyContent.Length() == 0 {
		log.Warn().Msg("No content found for markdown conversion")
		return md.String() + "\n\n*No article content was extracted.*\n\n"
	}

	// Log content statistics for debugging
	contentHTML, _ := bodyContent.Html()
	contentText := bodyContent.Text()
	log.Info().
		Int("content_html_length", len(contentHTML)).
		Int("content_text_length", len(contentText)).
		Int("content_words", len(strings.Fields(contentText))).
		Msg("Converting content to markdown")

	// Validate content quality before processing
	if !e.validateContentQuality(contentText) {
		log.Warn().Int("content_length", len(contentText)).Msg("Content quality validation failed")
	}

	// Convert HTML content to markdown with proper fragment handling
	e.convertNodeRecursive(bodyContent, &md, 0)

	// Add images section
	if len(images) > 0 {
		md.WriteString("\n\n---\n\n")
		md.WriteString("## Images\n\n")

		for i, img := range images {
			md.WriteString(fmt.Sprintf("### Image %d/%d\n\n", i+1, len(images)))
			md.WriteString("**[AI-Generated Description]**\n\n")
			md.WriteString(img.Description)
			md.WriteString("\n\n")
			md.WriteString(fmt.Sprintf("*Source: %s*\n\n", img.URL))

			if img.Alt != "" {
				md.WriteString(fmt.Sprintf("*Alt text: %s*\n\n", img.Alt))
			}

			md.WriteString("---\n\n")
		}
	}

	return md.String()
}


func (e *Extractor) cleanHTML(doc *goquery.Document) *goquery.Document {
	log.Info().Msg("🧹 Starting HTML cleaning")

	// Remove script, style, and other unwanted elements
	unwantedSelectors := []string{
		"script", "style", "noscript", "iframe", "embed", "object",
		"meta", "link", "title", "head",
		"nav", "header", "footer", "aside", "form",
		"input", "button", "select", "textarea", "canvas",
		"svg", "video", "audio", "source", "track",
	}

	removedCount := 0
	for _, selector := range unwantedSelectors {
		found := doc.Find(selector)
		count := found.Length()
		if count > 0 {
			found.Remove()
			removedCount += count
			log.Debug().Str("selector", selector).Int("removed", count).Msg("Removed elements")
		}
	}

	// Remove elements with JavaScript patterns in their content
	jsRemovedCount := 0
	doc.Find("*").Each(func(i int, s *goquery.Selection) {
		html, _ := s.Html()
		// Check if element contains JavaScript patterns
		if strings.Contains(html, "var ") ||
			strings.Contains(html, "function(") ||
			strings.Contains(html, "hbspt.") ||
			strings.Contains(html, "document.") ||
			strings.Contains(html, "window.") ||
			strings.Contains(html, "jQuery") ||
			strings.Contains(html, "$(") {
			s.Remove()
			jsRemovedCount++
		}
	})

	// Log content length after cleaning
	contentAfterCleaning := doc.Text()
	contentLength := len(strings.TrimSpace(contentAfterCleaning))
	log.Info().Int("elements_removed", removedCount).Int("js_elements_removed", jsRemovedCount).Int("content_length", contentLength).Msg("HTML cleaning completed")

	return doc
}

func (e *Extractor) shouldSkipElement(tagName string) bool {
	// Skip elements that should never be included in markdown
	skipElements := map[string]bool{
		"script":   true,
		"style":    true,
		"noscript": true,
		"iframe":   true,
		"embed":    true,
		"object":   true,
		"meta":     true,
		"link":     true,
		"title":    true,
		"head":     true,
		"html":     true,
		"body":     true,
		"nav":      true,
		"header":   true,
		"footer":   true,
		"aside":    true,
		"form":     true,
		"input":    true,
		"button":   true,
		"select":   true,
		"textarea": true,
		"canvas":   true,
		"svg":      true,
		"video":    true,
		"audio":    true,
		"source":   true,
		"track":    true,
	}
	return skipElements[tagName]
}

// extractContentFromDocument intelligently extracts content from HTML documents or fragments
func (e *Extractor) extractContentFromDocument(doc *goquery.Document) *goquery.Selection {
	// Try body first (full HTML documents)
	body := doc.Find("body").First()
	if body.Length() > 0 {
		bodyHTML, _ := body.Html()
		if len(bodyHTML) > 100 { // Reasonable content length
			log.Debug().Msg("Using body content for markdown conversion")
			return body
		}
	}

	// If body is empty or too short, this is likely an HTML fragment
	// Try common content containers
	contentSelectors := []string{
		"article", "main", ".article-content", ".post-content", ".entry-content",
		".content", "[role='main']", ".elementor-widget-theme-post-content",
		".elementor-widget-container", ".post", ".entry", ".story",
	}

	for _, selector := range contentSelectors {
		sel := doc.Find(selector).First()
		if sel.Length() > 0 {
			html, _ := sel.Html()
			if len(html) > 100 {
				log.Debug().Str("selector", selector).Int("length", len(html)).Msg("Using content selector")
				return sel
			}
		}
	}

	// Check if document itself is the content (fragment case)
	docHTML, _ := doc.Html()
	if len(docHTML) > 100 {
		log.Debug().Msg("Using document as content fragment")
		return doc.Selection
	}

	// Last resort: find the element with the most text content
	var bestElement *goquery.Selection
	maxTextLength := 0

	doc.Find("*").Each(func(i int, s *goquery.Selection) {
		text := strings.TrimSpace(s.Text())
		if len(text) > maxTextLength {
			maxTextLength = len(text)
			bestElement = s
		}
	})

	if bestElement != nil && maxTextLength > 200 {
		log.Debug().Int("text_length", maxTextLength).Msg("Using element with most text content")
		return bestElement
	}

	log.Warn().Msg("No suitable content found in document")
	return nil
}

// validateContentQuality checks if extracted content meets quality thresholds
func (e *Extractor) validateContentQuality(content string) bool {
	if len(content) == 0 {
		return false
	}

	// Basic content quality checks
	words := strings.Fields(content)
	wordCount := len(words)
	sentenceCount := len(strings.Split(content, "."))

	log.Debug().
		Int("word_count", wordCount).
		Int("sentence_count", sentenceCount).
		Int("char_count", len(content)).
		Msg("Content quality validation")

	// Check minimum thresholds
	if wordCount < 50 {
		log.Warn().Int("word_count", wordCount).Msg("Content too short (less than 50 words)")
		return false
	}

	if sentenceCount < 5 {
		log.Warn().Int("sentence_count", sentenceCount).Msg("Too few sentences (less than 5)")
		return false
	}

	// Check for repetitive content (indicates extraction issues)
	uniqueLines := make(map[string]bool)
	lines := strings.Split(content, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if len(line) > 10 {
			uniqueLines[line] = true
		}
	}

	if len(uniqueLines) < len(lines)/2 {
		log.Warn().Int("unique_lines", len(uniqueLines)).Int("total_lines", len(lines)).Msg("High content repetition detected")
		return false
	}

	log.Info().Int("word_count", wordCount).Msg("Content quality validation passed")
	return true
}

// convertNodeRecursive handles HTML fragments and ensures recursive processing
func (e *Extractor) convertNodeRecursive(sel *goquery.Selection, md *strings.Builder, depth int) {
	if sel == nil || sel.Length() == 0 {
		return
	}

	// Prevent infinite recursion
	if depth > 20 {
		log.Warn().Int("depth", depth).Msg("Maximum recursion depth exceeded")
		return
	}

	// For fragments, process all contents recursively
	sel.Contents().Each(func(i int, s *goquery.Selection) {
		e.processNode(s, md, depth+1)
	})
}

// processNode handles individual HTML elements with better content preservation
func (e *Extractor) processNode(sel *goquery.Selection, md *strings.Builder, depth int) {
	if sel == nil || sel.Length() == 0 {
		return
	}

	nodeName := goquery.NodeName(sel)

	// Skip processing if this element should be removed
	if e.shouldSkipElement(nodeName) {
		return
	}

	switch nodeName {
	case "#text":
		text := sel.Text()
		text = strings.TrimSpace(text)
		if text != "" {
			md.WriteString(text)
			// Add space after text unless it's followed by punctuation
			if !strings.HasSuffix(text, ".") && !strings.HasSuffix(text, ",") &&
			   !strings.HasSuffix(text, "!") && !strings.HasSuffix(text, "?") {
				md.WriteString(" ")
			}
		}

	case "h1", "h2", "h3", "h4", "h5", "h6":
		level := 0
		switch nodeName {
		case "h1": level = 1
		case "h2": level = 2
		case "h3": level = 3
		case "h4": level = 4
		case "h5": level = 5
		case "h6": level = 6
		}
		e.writeHeading(sel, md, level)

	case "p":
		md.WriteString("\n\n")
		e.convertNodeRecursive(sel, md, depth)
		md.WriteString("\n\n")

	case "br":
		md.WriteString("  \n")

	case "strong", "b":
		md.WriteString("**")
		e.convertNodeRecursive(sel, md, depth)
		md.WriteString("**")

	case "em", "i":
		md.WriteString("*")
		e.convertNodeRecursive(sel, md, depth)
		md.WriteString("*")

	case "code":
		md.WriteString("`")
		md.WriteString(sel.Text())
		md.WriteString("`")

	case "pre":
		md.WriteString("\n\n```\n")
		md.WriteString(sel.Text())
		md.WriteString("\n```\n\n")

	case "blockquote":
		md.WriteString("\n\n> ")
		text := strings.TrimSpace(sel.Text())
		text = strings.ReplaceAll(text, "\n", "\n> ")
		md.WriteString(text)
		md.WriteString("\n\n")

	case "ul", "ol":
		md.WriteString("\n\n")
		sel.Find("li").Each(func(idx int, li *goquery.Selection) {
			if nodeName == "ul" {
				md.WriteString("- ")
			} else {
				md.WriteString(fmt.Sprintf("%d. ", idx+1))
			}
			// Process list item contents properly
			li.Contents().Each(func(i int, item *goquery.Selection) {
				e.processNode(item, md, depth+1)
			})
			md.WriteString("\n")
		})
		md.WriteString("\n")

	case "a":
		href, exists := sel.Attr("href")
		text := strings.TrimSpace(sel.Text())
		if exists && text != "" {
			md.WriteString("[")
			md.WriteString(text)
			md.WriteString("](")
			md.WriteString(href)
			md.WriteString(")")
		} else if text != "" {
			md.WriteString(text)
		}

	case "img":
		// Images are handled separately in the images section
		// Skip inline images to avoid duplication

	case "hr":
		md.WriteString("\n\n---\n\n")

	case "div", "section", "article", "main", "span":
		// Process children recursively to preserve nested content
		e.convertNodeRecursive(sel, md, depth)

	default:
		// For unknown elements, process children to preserve content
		e.convertNodeRecursive(sel, md, depth)
	}
}

func (e *Extractor) writeHeading(s *goquery.Selection, md *strings.Builder, level int) {
	md.WriteString("\n\n")
	md.WriteString(strings.Repeat("#", level))
	md.WriteString(" ")
	md.WriteString(strings.TrimSpace(s.Text()))
	md.WriteString("\n\n")
}

func (e *Extractor) saveResult(jobID uuid.UUID, title, markdown string) (string, error) {
	// Ensure storage directory exists
	if err := os.MkdirAll(e.storagePath, 0755); err != nil {
		return "", fmt.Errorf("failed to create storage directory: %w", err)
	}

	// Sanitize title for filename
	filename := e.sanitizeFilename(title)
	if filename == "" {
		filename = jobID.String()
	}

	filepath := filepath.Join(e.storagePath, filename+".md")

	if err := os.WriteFile(filepath, []byte(markdown), 0644); err != nil {
		return "", fmt.Errorf("failed to write file: %w", err)
	}

	return filepath, nil
}

func (e *Extractor) sanitizeFilename(title string) string {
	// Remove invalid characters
	invalid := []string{"/", "\\", ":", "*", "?", "\"", "<", ">", "|"}
	filename := title
	for _, char := range invalid {
		filename = strings.ReplaceAll(filename, char, "")
	}

	// Replace spaces with underscores
	filename = strings.ReplaceAll(filename, " ", "_")

	// Limit length
	if len(filename) > 100 {
		filename = filename[:100]
	}

	return filename
}
