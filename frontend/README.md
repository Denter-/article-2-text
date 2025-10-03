# Article Extraction Tester - Frontend

React + TypeScript frontend for testing and debugging article extraction quality.

## Features

- **Simple Authentication** - Login with email/password
- **Extract Articles** - Submit URLs for extraction via UI
- **Live Updates** - Job status updates every 2 seconds
- **Quality Analysis** - Automatic detection of extraction issues
- **Comparison View** - Side-by-side Go vs Python baseline
- **API Key Management** - Get API key for programmatic access

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Go API server running on `localhost:8080`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:5173

### Build for Production

```bash
npm run build
```

## Usage

1. **Login**: Use credentials from database (`test@example.com` / `password123`)
2. **Extract**: Paste a URL and click "Extract"
3. **Monitor**: Watch job progress in real-time
4. **Review**: Click job to see details and quality issues
5. **Compare**: View side-by-side with Python baseline
6. **Download**: Save markdown files locally

## Tech Stack

- React 18 + TypeScript
- Vite (dev server & bundler)
- React Router (navigation)
- TanStack Query (API state management)
- Tailwind CSS (styling)
- Axios (HTTP client)
- React Markdown (preview rendering)

## API Integration

The frontend connects to the Go API at `http://localhost:8080`:

- `POST /api/v1/auth/login` - Authentication
- `POST /api/v1/extract/single` - Create extraction job
- `GET /api/v1/jobs` - List jobs (with pagination)
- `GET /api/v1/jobs/:id` - Get job details
- `GET /storage/{filename}.md` - Download markdown

## Configuration

Edit `vite.config.ts` to change API URL or proxy settings.

Default API URL: `http://localhost:8080`

## Quality Detection

The UI automatically detects common extraction issues:

- Navigation menus in content
- JavaScript code not removed
- Content starting too late (garbage at top)
- Excessive empty lines

These appear as warnings in the job detail view.

## Comparison Feature

The comparison view attempts to load Python baseline from `/results` directory:

- Matches by job title
- Shows side-by-side (first 1500 chars)
- Highlights quality differences
- Allows downloading both versions

If no baseline exists, it shows "No Python baseline found".

## Development Notes

- Auto-refreshes job list every 2 seconds
- Stops polling when job completes/fails
- Uses localStorage for JWT token
- Protected routes require authentication
