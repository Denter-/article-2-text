package extractor

// DefaultExclusions provides comprehensive CSS selectors for removing
// navigation, UI elements, and other non-content elements from articles.
// This is applied when no site-specific exclusions are configured.
var DefaultExclusions = []string{
	// Navigation and structure
	"nav", "header", "footer", "aside",
	"[role='navigation']", "[role='banner']", "[role='contentinfo']",
	"[role='complementary']", "[role='search']",

	// Menus and navigation
	"[class*='menu']", "[class*='navigation']", "[id*='menu']", "[id*='nav']",
	"[class*='breadcrumb']", "[id*='breadcrumb']", ".breadcrumb",
	"[class*='navbar']", "[id*='navbar']", ".navbar",
	"[class*='nav-menu']", "[class*='main-menu']",

	// Sidebars and widgets
	".sidebar", "[class*='sidebar']", "[id*='sidebar']",
	".widget", "[class*='widget']", "[id*='widget']",
	"[class*='sidebar-widget']", "[class*='widget-area']",

	// Comments and discussions
	"[id*='comment']", "[class*='comment']", ".comments",
	"[class*='discussion']", "[class*='comment-section']",
	"[id*='respond']", "[class*='respond']",

	// Social and sharing
	"[class*='share']", "[class*='social']", "[aria-label*='Share']",
	"[class*='follow']", "[data-share]", "[class*='social-share']",
	"[class*='social-media']", "[class*='social-links']",

	// Forms and CTAs
	"form", "[class*='newsletter']", "[class*='subscribe']",
	"[class*='signup']", "[class*='cta']", "[class*='call-to-action']",
	"[class*='email-signup']", "[class*='newsletter-signup']",
	"[class*='contact-form']", "[class*='lead-form']",

	// Related content
	".related", "[class*='related']", "[class*='recommend']",
	"[class*='popular']", "[class*='trending']", "[class*='similar']",
	"[class*='more-articles']", "[class*='read-more']",
	"[class*='related-posts']", "[class*='related-articles']",

	// Technical elements
	"script", "style", "noscript", "iframe", "embed", "object",
	"[class*='advertisement']", "[class*='ad-']", "[id*='ad-']",
	"[class*='banner']", "[class*='promo']",

	// Search elements
	"[class*='search']", "[id*='search']", "[role='search']",
	"[class*='search-box']", "[class*='search-form']",

	// WordPress/Elementor specific
	"[data-elementor-type='header']", "[data-elementor-type='footer']",
	"[data-elementor-type='sidebar']", "[data-elementor-type='widget']",
	".elementor-location-header", ".elementor-location-footer",
	".elementor-location-sidebar", ".elementor-widget-container",
	"[class*='elementor-widget']", "[class*='elementor-section']",

	// Common CMS elements
	"[class*='wp-block']", "[class*='gutenberg']",
	"[class*='jetpack']", "[class*='yoast']",
	"[class*='seo']", "[class*='meta']",

	// Third-party widgets
	"[class*='algolia']", "[id*='algolia']",
	"[class*='disqus']", "[id*='disqus']",
	"[class*='facebook']", "[class*='twitter']",
	"[class*='linkedin']", "[class*='instagram']",

	// HubSpot specific (ForEntrepreneurs uses this)
	"[class*='hs-']", "[id*='hs-']", "[data-hs-]",
	"[class*='hubspot']", "[id*='hubspot']",
	"[class*='hbspt']", "[id*='hbspt']",

	// Generic UI elements
	"[class*='button']", "[class*='btn']", "[type='button']",
	"[class*='link']", "[class*='anchor']",
	"[class*='icon']", "[class*='logo']",
	"[class*='brand']", "[class*='site-title']",
	"[class*='site-description']", "[class*='tagline']",

	// Skip links and accessibility
	"[class*='skip']", "[id*='skip']", ".screen-reader-text",
	"[class*='sr-only']", "[class*='visually-hidden']",

	// Pagination
	"[class*='pagination']", "[class*='pager']", "[class*='page-nav']",
	"[class*='next']", "[class*='prev']", "[class*='previous']",

	// Author info (often in sidebars)
	"[class*='author-bio']", "[class*='author-info']",
	"[class*='author-card']", "[class*='author-box']",

	// Tags and categories (often in sidebars)
	"[class*='tag']", "[class*='category']", "[class*='taxonomy']",
	"[class*='post-meta']", "[class*='entry-meta']",

	// Table of contents
	"[class*='toc']", "[class*='table-of-contents']",
	"[id*='toc']", "[id*='table-of-contents']",

	// Print and mobile specific
	"[class*='print']", "[class*='mobile']", "[class*='desktop']",
	"[class*='hidden']", "[class*='visible']",

	// Generic containers that might be empty or contain UI
	"[class*='container']", "[class*='wrapper']", "[class*='inner']",
	"[class*='content-wrapper']", "[class*='main-wrapper']",

	// Common non-content classes
	"[class*='utility']", "[class*='helper']", "[class*='tool']",
	"[class*='plugin']", "[class*='addon']", "[class*='extension']",
}


