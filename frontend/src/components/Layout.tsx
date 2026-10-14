import { Link, Outlet, useLocation } from 'react-router-dom'
import { Mic2, Activity, Home } from 'lucide-react'
import { clsx } from 'clsx'
import BackendStatus from './BackendStatus'

export default function Layout() {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Home', icon: Home },
    { path: '/analyze', label: 'Analyze', icon: Mic2 },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-surface-600 bg-surface-800/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-lg bg-primary-600 flex items-center justify-center group-hover:bg-primary-500 transition-colors">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="font-bold text-white text-lg leading-none">Vox</span>
                <div className="text-xs text-gray-400 leading-none">Speech Analytics</div>
              </div>
            </Link>

            <nav className="flex items-center gap-1">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                    location.pathname === path
                      ? 'bg-primary-600/20 text-primary-400'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-surface-700'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              ))}
            </nav>

            <BackendStatus />
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-surface-600 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm text-gray-500">
            Vox — Counterpointing Speech Analytics &amp; Temporal Flaw Finding
          </p>
        </div>
      </footer>
    </div>
  )
}
