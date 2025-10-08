package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/Denter-/article-extraction/worker/internal/extractor"
	"github.com/Denter-/article-extraction/worker/internal/gemini"
	"github.com/Denter-/article-extraction/worker/internal/repository"
	"github.com/google/uuid"
)

func main() {
	fmt.Println("🚀 Direct Go Worker Test")
	fmt.Println("========================")

	// Initialize components
	geminiClient := &gemini.Client{} // We'll skip actual Gemini calls for this test
	extractor := extractor.New(geminiClient, "./test_storage", "./config/sites")

	// Create a test job
	jobID := uuid.New()
	job := &repository.Job{
		ID:  jobID,
		URL: "https://forentrepreneurs.com/saas-metrics-2/",
		Domain: "forentrepreneurs.com",
	}

	fmt.Printf("Testing URL: %s\n", job.URL)
	fmt.Printf("Job ID: %s\n", jobID.String())
	fmt.Println()

	// Run extraction
	ctx := context.Background()
	fmt.Println("⏳ Starting extraction...")
	startTime := time.Now()

	result, err := extractor.Extract(ctx, job, nil)
	if err != nil {
		log.Fatalf("❌ Extraction failed: %v", err)
	}

	duration := time.Since(startTime)
	fmt.Printf("✅ Extraction completed in %v\n", duration)
	fmt.Printf("📄 Result file: %s\n", result.Path)
	fmt.Printf("📊 Word count: %d\n", result.WordCount)
	fmt.Printf("🖼️  Image count: %d\n", result.ImageCount)
	fmt.Printf("📝 Title: %s\n", result.Title)
	fmt.Printf("✍️  Author: %s\n", result.Author)
	fmt.Println()

	// Content quality assessment
	fmt.Println("📈 Content Quality Assessment:")
	fmt.Println("===============================")

	if result.WordCount > 7000 {
		fmt.Printf("✅ EXCELLENT: %d words (expected ~7,711)\n", result.WordCount)
	} else if result.WordCount > 5000 {
		fmt.Printf("⚠️  GOOD: %d words (expected ~7,711, but substantial content)\n", result.WordCount)
	} else if result.WordCount > 1000 {
		fmt.Printf("⚠️  FAIR: %d words (much less than expected ~7,711)\n", result.WordCount)
	} else {
		fmt.Printf("❌ POOR: %d words (critical content loss still present)\n", result.WordCount)
	}

	// Check for actual article content by looking at markdown content
	if len(result.Markdown) > 10000 {
		fmt.Printf("✅ Content length: %d characters (substantial)\n", len(result.Markdown))
	} else {
		fmt.Printf("❌ Content length: %d characters (too short)\n", len(result.Markdown))
	}

	// Look for key indicators of article content
	hasArticleContent := false
	if strings.Contains(result.Markdown, "If you cannot measure it, you cannot improve it") {
		hasArticleContent = true
		fmt.Println("✅ Found article opening quote")
	}
	if strings.Contains(result.Markdown, "Lord Kelvin") {
		hasArticleContent = true
		fmt.Println("✅ Found attribution quote")
	}
	if strings.Contains(result.Markdown, "##") || strings.Contains(result.Markdown, "###") {
		fmt.Println("✅ Found markdown headers (indicates structure)")
	}

	if !hasArticleContent {
		fmt.Println("❌ No article content markers found")
	}

	fmt.Println()
	fmt.Println("📝 First 500 characters of markdown:")
	fmt.Println("===================================")
	if len(result.Markdown) > 500 {
		fmt.Println(result.Markdown[:500])
	} else {
		fmt.Println(result.Markdown)
	}
	fmt.Println("...")

	// Final assessment
	fmt.Println()
	fmt.Println("🎯 FINAL QA ASSESSMENT:")
	fmt.Println("======================")

	if result.WordCount > 7000 && hasArticleContent {
		fmt.Println("🟢 FIX SUCCESSFUL: Content extraction is working correctly")
		fmt.Println("   The critical content loss issue has been resolved")
	} else if result.WordCount > 1000 && hasArticleContent {
		fmt.Println("🟡 PARTIAL FIX: Some content is being extracted but not fully")
		fmt.Println("   Further optimization may be needed")
	} else {
		fmt.Println("🔴 FIX FAILED: Critical content loss issue still persists")
		fmt.Println("   The extraction is still not working properly")
	}
}