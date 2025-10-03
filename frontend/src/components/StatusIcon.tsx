import { CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react';

type StatusType = 'completed' | 'processing' | 'failed' | 'queued';

export default function StatusIcon({ status }: { status: StatusType }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
    case 'processing':
      return <Loader2 className="w-5 h-5 text-amber-600 animate-spin" />;
    case 'failed':
      return <XCircle className="w-5 h-5 text-rose-600" />;
    case 'queued':
      return <Clock className="w-5 h-5 text-slate-500" />;
    default:
      return <Clock className="w-5 h-5 text-slate-500" />;
  }
}



