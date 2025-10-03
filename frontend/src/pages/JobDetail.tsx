import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { jobsApi } from '../lib/api';
import { formatDate, getStatusIcon, detectQualityIssues } from '../lib/utils';

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [markdown, setMarkdown] = useState<string>('');
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');

  // Fetch job details
  const { data, isLoading } = useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.get(id!),
    refetchInterval: (query) => {
      const job = query.state.data?.job;
      // Stop polling if completed or failed
      return job?.status === 'completed' || job?.status === 'failed' ? false : 2000;
    },
  });

  const job = data?.job;

  // Use markdown from database or load from file
  useEffect(() => {
    if (job?.markdown_content) {
      setMarkdown(job.markdown_content);
    } else if (job?.result_path) {
      jobsApi
        .downloadMarkdown(job.result_path)
        .then(setMarkdown)
        .catch(console.error);
    }
  }, [job?.markdown_content, job?.result_path]);

  const qualityIssues = markdown ? detectQualityIssues(markdown) : [];
  const preview = markdown.slice(0, 2000);

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="text-center py-12">Loading...</div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="text-center py-12">
          <p className="text-gray-500">Job not found</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      {/* Back Button */}
      <Link
        to="/"
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6"
      >
        ← Back to Dashboard
      </Link>

      {/* Job Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{getStatusIcon(job.status)}</span>
              <h1 className="text-2xl font-bold text-gray-900">
                {job.title || 'Untitled'}
              </h1>
            </div>
            <p className="text-gray-600">{job.url}</p>
          </div>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4 border-t border-gray-200">
          <div>
            <p className="text-sm text-gray-500">Status</p>
            <p className="font-medium capitalize">{job.status}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Word Count</p>
            <p className="font-medium">{job.word_count?.toLocaleString() || '-'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Images</p>
            <p className="font-medium">{job.image_count ?? '-'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Processing Time</p>
            <p className="font-medium">
              {job.started_at && job.completed_at
                ? `${Math.round(
                    (new Date(job.completed_at).getTime() -
                      new Date(job.started_at).getTime()) /
                      1000
                  )}s`
                : '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Domain</p>
            <p className="font-medium">{job.domain}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Credits Used</p>
            <p className="font-medium">{job.credits_used}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Created</p>
            <p className="font-medium">{formatDate(job.created_at)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Worker</p>
            <p className="font-medium">{job.worker_type || 'Go'}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-4">
          {job.status === 'completed' && job.result_path && (
            <>
              <button
                onClick={async () => {
                  const blob = new Blob([markdown], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${job.title || 'article'}.md`;
                  a.click();
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Download Markdown
              </button>
              <button
                onClick={() => navigate(`/job/${id}/compare`)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                View Comparison
              </button>
            </>
          )}
        </div>

        {/* Progress */}
        {job.status === 'processing' && (
          <div className="mt-4 p-4 bg-blue-50 rounded-md">
            <div className="flex items-center gap-2 mb-2">
              <div className="flex-1 bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${job.progress_percent}%` }}
                ></div>
              </div>
              <span className="text-sm text-blue-800">{job.progress_percent}%</span>
            </div>
            {job.progress_message && (
              <p className="text-sm text-blue-800">{job.progress_message}</p>
            )}
          </div>
        )}

        {/* Error */}
        {job.status === 'failed' && job.error_message && (
          <div className="mt-4 p-4 bg-red-50 rounded-md">
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-sm text-red-700 mt-1">{job.error_message}</p>
          </div>
        )}
      </div>

      {/* Quality Issues */}
      {qualityIssues.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-yellow-900 mb-3">
            ⚠️ Quality Warnings
          </h2>
          <ul className="space-y-2">
            {qualityIssues.map((issue, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-yellow-600 mt-1">•</span>
                <div>
                  <p className="text-sm font-medium text-yellow-900">
                    {issue.type.charAt(0).toUpperCase() + issue.type.slice(1)} Issue
                    (
                    {issue.severity})
                  </p>
                  <p className="text-sm text-yellow-800">{issue.message}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Preview */}
      {job.status === 'completed' && markdown && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold">📄 Content Preview</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('preview')}
                className={`px-3 py-1 text-sm rounded-md ${
                  viewMode === 'preview'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                Preview
              </button>
              <button
                onClick={() => setViewMode('code')}
                className={`px-3 py-1 text-sm rounded-md ${
                  viewMode === 'code'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                Raw
              </button>
            </div>
          </div>

          <div className="p-6">
            {viewMode === 'preview' ? (
              <div className="prose max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {preview}
                </ReactMarkdown>
                {markdown.length > 2000 && (
                  <p className="text-gray-500 italic mt-4">
                    ... (showing first 2000 characters, download for full content)
                  </p>
                )}
              </div>
            ) : (
              <pre className="text-sm bg-gray-50 p-4 rounded-md overflow-x-auto max-h-96 overflow-y-auto">
                {preview}
                {markdown.length > 2000 && '\n\n... (truncated)'}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

