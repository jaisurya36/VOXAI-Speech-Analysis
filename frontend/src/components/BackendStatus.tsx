import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { apiService } from '../services/api'

type Status = 'checking' | 'online' | 'offline'

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    const check = async () => {
      try {
        await apiService.health()
        setStatus('online')
      } catch {
        setStatus('offline')
      }
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={clsx(
      'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border',
      status === 'online' && 'bg-emerald-950 border-emerald-700 text-emerald-400',
      status === 'offline' && 'bg-red-950 border-red-700 text-red-400',
      status === 'checking' && 'bg-surface-700 border-surface-500 text-gray-400',
    )}>
      {status === 'checking' && <Loader2 className="w-3 h-3 animate-spin" />}
      {status === 'online' && <CheckCircle2 className="w-3 h-3" />}
      {status === 'offline' && <XCircle className="w-3 h-3" />}
      <span>
        {status === 'checking' ? 'Connecting...' : status === 'online' ? 'API Online' : 'API Offline'}
      </span>
    </div>
  )
}
