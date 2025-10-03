import { Link, useLocation } from 'react-router-dom';
import { FileText, Key, LogOut, User } from 'lucide-react';
import { useAuth } from '../lib/auth';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  if (!user) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2 text-xl font-bold text-slate-900 hover:text-indigo-600 transition-colors">
                <FileText className="w-6 h-6 text-indigo-600" />
                Article Extractor
              </Link>

              <nav className="flex gap-2">
                <Link
                  to="/"
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    location.pathname === '/'
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  Dashboard
                </Link>
                <Link
                  to="/api-key"
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    location.pathname === '/api-key'
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <Key className="w-4 h-4" />
                  API Key
                </Link>
              </nav>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3 px-4 py-2 bg-slate-50 rounded-lg border border-slate-200">
                <User className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-700">{user.email}</span>
                <span className="text-slate-300">•</span>
                <span className="text-sm font-semibold text-indigo-600">{user.credits.toLocaleString()} credits</span>
              </div>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>{children}</main>
    </div>
  );
}

