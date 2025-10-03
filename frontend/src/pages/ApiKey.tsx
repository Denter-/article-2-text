import { useState } from 'react';
import { useAuth } from '../lib/auth';
import { Link } from 'react-router-dom';

export default function ApiKey() {
  const { user } = useAuth();
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    if (user?.api_key) {
      navigator.clipboard.writeText(user.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <Link
        to="/"
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6"
      >
        ← Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold mb-6">API Key Management</h1>

      {/* API Key Display */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Your API Key</h2>
        <div className="flex items-center gap-3 mb-4">
          <code className="flex-1 px-4 py-3 bg-gray-50 rounded-md text-sm font-mono border border-gray-200">
            {user.api_key}
          </code>
          <button
            onClick={copyToClipboard}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 whitespace-nowrap"
          >
            {copied ? '✓ Copied!' : '📋 Copy'}
          </button>
        </div>
        <p className="text-sm text-gray-600">
          Keep this key secure. It provides full access to your account.
        </p>
      </div>

      {/* Usage Stats */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Usage This Month</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-500">Credits Remaining</p>
            <p className="text-2xl font-bold text-gray-900">{user.credits.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Tier</p>
            <p className="text-2xl font-bold text-gray-900 capitalize">{user.tier}</p>
          </div>
        </div>
      </div>

      {/* API Documentation */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">📖 API Documentation</h2>

        <div className="space-y-6">
          <div>
            <h3 className="font-medium mb-2">Extract an Article</h3>
            <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto">
{`curl -X POST http://localhost:8080/api/v1/extract/single \\
  -H "X-API-Key: ${user.api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://example.com/article"
  }'`}
            </pre>
          </div>

          <div>
            <h3 className="font-medium mb-2">Check Job Status</h3>
            <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto">
{`curl http://localhost:8080/api/v1/jobs/{job_id} \\
  -H "X-API-Key: ${user.api_key}"`}
            </pre>
          </div>

          <div>
            <h3 className="font-medium mb-2">List Your Jobs</h3>
            <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto">
{`curl "http://localhost:8080/api/v1/jobs?limit=10" \\
  -H "X-API-Key: ${user.api_key}"`}
            </pre>
          </div>

          <div>
            <h3 className="font-medium mb-2">Download Extracted Content</h3>
            <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto">
{`# The result_path is returned in the job response
curl http://localhost:8080/storage/{filename}.md`}
            </pre>
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-md">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> All API requests require authentication. You can use either the{' '}
            <code className="bg-blue-100 px-1 rounded">X-API-Key</code> header or{' '}
            <code className="bg-blue-100 px-1 rounded">Authorization: Bearer</code> token.
          </p>
        </div>
      </div>
    </div>
  );
}



