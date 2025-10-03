import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { jobsApi } from '../lib/api';
import { detectQualityIssues } from '../lib/utils';
import axios from 'axios';

export default function JobComparison() {
  const { id } = useParams<{ id: string }>();
  const [goMarkdown, setGoMarkdown] = useState<string>('');
  const [pythonMarkdown, setPythonMarkdown] = useState<string>('');
  const [pythonError, setPythonError] = useState<string>('');

  const { data } = useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.get(id!),
  });

  const job = data?.job;

  // Load Go worker markdown
  useEffect(() => {
    if (job?.result_path) {
      jobsApi.downloadMarkdown(job.result_path).then(setGoMarkdown).catch(console.error);
    }
  }, [job?.result_path]);

  // Try to load Python baseline from /results
  useEffect(() => {
    if (job?.title) {
      // Try to find matching Python baseline file
      const possibleFilenames = [
        job.title.replace(/[^a-zA-Z0-9_-]/g, '_') + '.md',
        job.title.replace(/\s+/g, '_') + '.md',
      ];

      Promise.any(
        possibleFilenames.map((filename) =>
          axios.get(`http://localhost:8080/results/${filename}`)
        )
      )
        .then((response) => setPythonMarkdown(response.data))
        .catch(() =>
          setPythonError('No Python baseline found for comparison')
        );
    }
  }, [job?.title]);

  const goIssues = goMarkdown ? detectQualityIssues(goMarkdown) : [];
  const pythonIssues = pythonMarkdown ? detectQualityIssues(pythonMarkdown) : [];

  const goWordCount = goMarkdown.split(/\s+/).length;
  const pythonWordCount = pythonMarkdown.split(/\s+/).length;
  const wordDiff =
    pythonWordCount > 0
      ? Math.round(((goWordCount - pythonWordCount) / pythonWordCount) * 100)
      : 0;

  if (!job) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4">
        <div className="text-center py-12">Loading...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <Link
        to={`/job/${id}`}
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6"
      >
        ← Back to Job
      </Link>

      <h1 className="text-2xl font-bold mb-6">Extraction Comparison</h1>

      {/* Metrics Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500 mb-1">Go Worker (NEW)</p>
          <p className="text-2xl font-bold text-gray-900">
            {goWordCount.toLocaleString()} words
          </p>
          <p className="text-sm text-gray-600 mt-2">
            {goIssues.length} issues detected
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500 mb-1">Python (BASELINE)</p>
          <p className="text-2xl font-bold text-gray-900">
            {pythonMarkdown
              ? `${pythonWordCount.toLocaleString()} words`
              : 'Not available'}
          </p>
          <p className="text-sm text-gray-600 mt-2">
            {pythonIssues.length} issues detected
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500 mb-1">Difference</p>
          <p
            className={`text-2xl font-bold ${
              wordDiff > 20 ? 'text-red-600' : 'text-green-600'
            }`}
          >
            {wordDiff > 0 ? '+' : ''}
            {wordDiff}%
          </p>
          <p className="text-sm text-gray-600 mt-2">
            {wordDiff > 20 ? 'Too much content' : 'Within range'}
          </p>
        </div>
      </div>

      {/* Issues Summary */}
      {(goIssues.length > 0 || pythonIssues.length > 0) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">🔍 Detected Issues</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Go Worker</h3>
              {goIssues.length === 0 ? (
                <p className="text-sm text-gray-600">✅ No issues detected</p>
              ) : (
                <ul className="space-y-1">
                  {goIssues.map((issue, i) => (
                    <li key={i} className="text-sm text-yellow-800">
                      • {issue.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-2">Python Baseline</h3>
              {pythonIssues.length === 0 ? (
                <p className="text-sm text-gray-600">✅ No issues detected</p>
              ) : (
                <ul className="space-y-1">
                  {pythonIssues.map((issue, i) => (
                    <li key={i} className="text-sm text-yellow-800">
                      • {issue.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Side-by-Side Comparison */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Side-by-Side Comparison</h2>
          <p className="text-sm text-gray-600 mt-1">
            First 1500 characters of each version
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-gray-200">
          {/* Go Worker */}
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">Go Worker (NEW)</h3>
              {goIssues.length > 0 && (
                <span className="text-sm text-red-600">
                  ❌ {goIssues.length} issues
                </span>
              )}
            </div>
            <pre className="text-xs bg-gray-50 p-4 rounded-md overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap">
              {goMarkdown.slice(0, 1500)}
              {goMarkdown.length > 1500 && '\n\n... (truncated)'}
            </pre>
          </div>

          {/* Python Baseline */}
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">Python (BASELINE)</h3>
              {pythonIssues.length === 0 && pythonMarkdown && (
                <span className="text-sm text-green-600">✅ Clean</span>
              )}
            </div>
            {pythonError ? (
              <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-md">
                {pythonError}
              </div>
            ) : (
              <pre className="text-xs bg-gray-50 p-4 rounded-md overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap">
                {pythonMarkdown.slice(0, 1500)}
                {pythonMarkdown.length > 1500 && '\n\n... (truncated)'}
              </pre>
            )}
          </div>
        </div>
      </div>

      {/* Download Both */}
      <div className="mt-6 flex gap-3">
        <button
          onClick={() => {
            const blob = new Blob([goMarkdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${job.title || 'article'}_go.md`;
            a.click();
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Download Go Version
        </button>

        {pythonMarkdown && (
          <button
            onClick={() => {
              const blob = new Blob([pythonMarkdown], { type: 'text/markdown' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${job.title || 'article'}_python.md`;
              a.click();
            }}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            Download Python Baseline
          </button>
        )}
      </div>
    </div>
  );
}



