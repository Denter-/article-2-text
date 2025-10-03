import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileText, Download, Eye, AlertCircle } from 'lucide-react';
import { jobsApi } from '../lib/api';
import { formatDate, getStatusIcon, getStatusColor } from '../lib/utils';
import { useWebSocket } from '../lib/useWebSocket';
import StatusIcon from '../components/StatusIcon';
import type { Job } from '../types';

export default function Dashboard() {
  const [url, setUrl] = useState('');
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Connect to WebSocket for real-time updates
  const { isConnected } = useWebSocket();

  // Fetch jobs once on mount, WebSocket will trigger updates
  const { data, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list(20, 0),
    // No polling! WebSocket will handle updates
  });

  // Create job mutation
  const createJob = useMutation({
    mutationFn: jobsApi.create,
    onSuccess: () => {
      setUrl('');
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      createJob.mutate({ url: url.trim() });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-3 flex items-center gap-3">
            <FileText className="w-10 h-10 text-indigo-600" />
            Article Extraction Tester
          </h1>
          <p className="text-slate-600 text-lg">
            Test and debug article extraction quality with AI-powered analysis
          </p>
        </div>

        {/* Extract Form */}
        <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-8 mb-8">
          <h2 className="text-xl font-semibold mb-5 flex items-center gap-2 text-slate-900">
            <FileText className="w-5 h-5 text-indigo-600" />
            Extract New Article
          </h2>
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/article"
              required
              className="flex-1 px-5 py-3 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
            <button
              type="submit"
              disabled={createJob.isPending}
              className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-lg hover:from-indigo-700 hover:to-indigo-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-all shadow-md hover:shadow-lg"
            >
              {createJob.isPending ? 'Extracting...' : 'Extract Article'}
            </button>
          </form>

          {createJob.isError && (
            <div className="mt-5 rounded-lg bg-rose-50 border border-rose-200 p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-rose-800">
                {(createJob.error as any)?.response?.data?.error ||
                  'Failed to create extraction job'}
              </p>
            </div>
          )}

          {createJob.isSuccess && (
            <div className="mt-5 rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-start gap-3">
              <StatusIcon status="completed" />
              <p className="text-sm text-emerald-800 font-medium">
                Job created! Processing in background...
              </p>
            </div>
          )}
        </div>

        {/* Jobs List */}
        <div className="bg-white rounded-xl shadow-lg border border-slate-200">
          <div className="px-8 py-6 border-b border-slate-200">
            <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-600" />
              Recent Extractions
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Last {data?.jobs?.length || 0} extractions • Auto-refreshing every 2 seconds
            </p>
          </div>

          {isLoading ? (
            <div className="p-12 text-center">
              <StatusIcon status="processing" />
              <p className="mt-4 text-slate-500">Loading extractions...</p>
            </div>
          ) : !data?.jobs || data.jobs.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-600 font-medium">No extractions yet</p>
              <p className="text-slate-400 text-sm mt-1">Try extracting an article above to get started!</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {data.jobs.map((job: Job) => (
                <div
                  key={job.id}
                  className="p-6 hover:bg-slate-50 cursor-pointer transition-colors group"
                  onClick={() => navigate(`/job/${job.id}`)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <StatusIcon status={getStatusIcon(job.status)} />
                        <h3 className="text-lg font-semibold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                          {job.title || 'Untitled'}
                        </h3>
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(
                            job.status
                          )}`}
                        >
                          {job.status}
                        </span>
                      </div>

                      <p className="text-sm text-slate-500 truncate mb-3">{job.url}</p>

                      <div className="flex items-center gap-4 text-sm text-slate-600">
                        {job.word_count && (
                          <span className="flex items-center gap-1">
                            <FileText className="w-4 h-4" />
                            {job.word_count.toLocaleString()} words
                          </span>
                        )}
                        {job.image_count !== undefined && (
                          <span>{job.image_count} images</span>
                        )}
                        {job.completed_at && job.started_at && (
                          <span>
                            ⏱ {Math.round(
                              (new Date(job.completed_at).getTime() -
                                new Date(job.started_at).getTime()) /
                                1000
                            )}s
                          </span>
                        )}
                        <span className="text-slate-400">{formatDate(job.created_at)}</span>
                      </div>

                      {job.status === 'processing' && job.progress_message && (
                        <div className="mt-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="flex-1 bg-amber-200 rounded-full h-2">
                              <div
                                className="bg-amber-500 h-2 rounded-full transition-all"
                                style={{ width: `${job.progress_percent}%` }}
                              ></div>
                            </div>
                            <span className="text-xs font-medium text-amber-700">
                              {job.progress_percent}%
                            </span>
                          </div>
                          <p className="text-xs text-amber-700">
                            {job.progress_message}
                          </p>
                        </div>
                      )}

                      {job.status === 'failed' && job.error_message && (
                        <div className="mt-3 p-3 bg-rose-50 rounded-lg border border-rose-200 flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-rose-700">
                            {job.error_message}
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/job/${job.id}`);
                        }}
                        className="px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors flex items-center gap-1"
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </button>
                      {job.status === 'completed' && job.result_path && (
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            const content = await jobsApi.downloadMarkdown(
                              job.result_path!
                            );
                            const blob = new Blob([content], { type: 'text/markdown' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${job.title || 'article'}.md`;
                            a.click();
                          }}
                          className="px-4 py-2 text-sm font-medium text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors flex items-center gap-1"
                        >
                          <Download className="w-4 h-4" />
                          Download
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

