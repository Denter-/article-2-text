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

func (e *Extractor) Extract(ctx context.Context, job *repository.Job) (*ExtractionResult, error) {
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

	// Load site config
	domain, _ := e.getDomainFromURL(job.URL)
	config, err := e.loadSiteConfig(domain)
	if err != nil {
		log.Warn().Err(err).Str("domain", domain).Msg("Failed to load site config, forwarding to Python AI worker")
		// Forward to Python AI worker for learning
		return e.ForwardToPythonAIWorker(ctx, job)
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

	// The Python AI worker will update the job in the database
	// We'll return a placeholder result since the Python worker handles everything
	return &ExtractionResult{
		Path:       "python-ai-worker-handled",
		Markdown:   "Content extracted by Python AI worker",
		Title:      "AI Learning in Progress",
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
	doc, err := goquery.NewDocumentFromReader(strings.NewReader("<div>" + html + "</div>"))
	if err != nil {
		return html
	}

	root := doc.Find("div").First()

	// Use comprehensive default exclusions if none specified
	if len(excludeSelectors) == 0 {
		excludeSelectors = DefaultExclusions
	}

	// Remove excluded elements
	totalRemoved := 0
	for _, selector := range excludeSelectors {
		found := root.Find(selector)
		count := found.Length()
		if count > 0 {
			found.Remove()
			totalRemoved += count
			log.Debug().Str("selector", selector).Int("removed", count).Msg("Removed elements")
		}
	}

	log.Info().Int("total_excluded", totalRemoved).Int("exclusion_rules", len(excludeSelectors)).Msg("Applied exclusions")

	// Get the cleaned HTML
	cleanedHTML, _ := root.Html()
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
	resp, err := e.httpClient.Get(urlStr)
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

	// Convert HTML content to markdown
	e.convertNode(doc.Selection, &md, 0)

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

func (e *Extractor) convertNode(sel *goquery.Selection, md *strings.Builder, depth int) {
	sel.Contents().Each(func(i int, s *goquery.Selection) {
		nodeName := goquery.NodeName(s)

		switch nodeName {
		case "#text":
			text := s.Text()
			text = strings.TrimSpace(text)
			if text != "" {
				md.WriteString(text)
				md.WriteString(" ")
			}

		case "h1":
			e.writeHeading(s, md, 1)
		case "h2":
			e.writeHeading(s, md, 2)
		case "h3":
			e.writeHeading(s, md, 3)
		case "h4":
			e.writeHeading(s, md, 4)
		case "h5":
			e.writeHeading(s, md, 5)
		case "h6":
			e.writeHeading(s, md, 6)

		case "p":
			md.WriteString("\n\n")
			e.convertNode(s, md, depth)
			md.WriteString("\n\n")

		case "br":
			md.WriteString("  \n")

		case "strong", "b":
			md.WriteString("**")
			e.convertNode(s, md, depth)
			md.WriteString("**")

		case "em", "i":
			md.WriteString("*")
			e.convertNode(s, md, depth)
			md.WriteString("*")

		case "code":
			md.WriteString("`")
			md.WriteString(s.Text())
			md.WriteString("`")

		case "pre":
			md.WriteString("\n\n```\n")
			md.WriteString(s.Text())
			md.WriteString("\n```\n\n")

		case "blockquote":
			md.WriteString("\n\n> ")
			text := strings.TrimSpace(s.Text())
			text = strings.ReplaceAll(text, "\n", "\n> ")
			md.WriteString(text)
			md.WriteString("\n\n")

		case "ul", "ol":
			md.WriteString("\n\n")
			s.Find("li").Each(func(idx int, li *goquery.Selection) {
				if nodeName == "ul" {
					md.WriteString("- ")
				} else {
					md.WriteString(fmt.Sprintf("%d. ", idx+1))
				}
				md.WriteString(strings.TrimSpace(li.Text()))
				md.WriteString("\n")
			})
			md.WriteString("\n")

		case "a":
			href, exists := s.Attr("href")
			text := strings.TrimSpace(s.Text())
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
			// Just process children
			e.convertNode(s, md, depth)

		default:
			// For unknown elements, just process children
			e.convertNode(s, md, depth)
		}
	})
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


