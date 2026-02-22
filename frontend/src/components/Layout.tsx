import { useMemo, useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const SIDEBAR_KEY = 'mp_sidebar_collapsed';

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(SIDEBAR_KEY) === '1'; } catch { return false; }
  });

  useEffect(() => {
    try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0'); } catch {}
  }, [collapsed]);

  const navItems = useMemo(() => [
    { path: '/', label: 'Dashboard', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    )},
    { path: '/products', label: 'Products', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
    )},
    { path: '/ads', label: 'Ads', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
      </svg>
    )},
    { path: '/price-monitor', label: 'Price Monitor', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    )},
    { path: '/sellers', label: 'Sellers', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    )},
    { path: '/hepsiburada', label: 'Hepsiburada', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
      </svg>
    )},
    { path: '/trendyol', label: 'Trendyol', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    )},
    { path: '/web-products', label: 'Web Products', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )},
    { path: '/category-explorer', label: 'Category Explorer', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    )},
    { path: '/url-scraper', label: 'URL Scraper', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    )},
    { path: '/video-transcripts', label: 'Transcripts', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4V20M17 4V20M3 8H7M17 8H21M3 12H21M3 16H7M17 16H21M7 20H17" />
      </svg>
    )},
    { path: '/json-editor', label: 'JSON Editor', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    )},
  ], []);

  const activeLabel = useMemo(() => {
    const activeItem = navItems.find((item) => item.path === location.pathname);
    return activeItem?.label || 'Workspace';
  }, [location.pathname, navItems]);

  const sidebarWidth = collapsed ? 'w-[72px]' : 'w-72';
  const mainMargin = collapsed ? 'md:ml-[72px]' : 'md:ml-72';

  return (
    <div className="min-h-screen app-shell text-[#5f471d] flex">
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`${sidebarWidth} sidebar-surface flex flex-col fixed h-full z-50 transition-all duration-300 ease-in-out ${
          mobileOpen ? 'translate-x-0 !w-72' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className={`border-b border-[#5b4824]/10 transition-all duration-300 ${collapsed ? 'p-3' : 'p-6'}`}>
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3 min-w-0">
              <div className="w-11 h-11 rounded-xl brand-mark flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              {!collapsed && (
                <div className="min-w-0">
                  <span className="text-xl font-bold text-[#3a2d14] tracking-tight">MarketPulse</span>
                  <span className="text-xs text-[#9e8b66] block">Intelligence Console</span>
                </div>
              )}
            </Link>
            <button
              onClick={() => setMobileOpen(false)}
              className="p-2 text-[#9e8b66] hover:text-[#5b4824] hover:bg-[#5b4824]/10 rounded-lg transition-colors md:hidden"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <nav className={`flex-1 overflow-y-auto transition-all duration-300 ${collapsed ? 'p-2' : 'p-4'}`}>
          <div className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  title={collapsed ? item.label : undefined}
                  className={`nav-item flex items-center rounded-xl text-sm font-semibold transition-all duration-200 ${
                    collapsed ? 'justify-center px-0 py-3' : 'gap-3 px-4 py-3'
                  } ${isActive ? 'nav-item-active text-[#3a2d14]' : 'text-[#7a6b4e]'}`}
                >
                  <span className={`flex-shrink-0 ${isActive ? 'text-[#5b4824]' : 'text-[#9e8b66]'}`}>
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <>
                      <span className="truncate">{item.label}</span>
                      {isActive && (
                        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#f7ce86] shadow-glow-cyan flex-shrink-0" />
                      )}
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        </nav>

        <div className={`border-t border-[#5b4824]/10 transition-all duration-300 ${collapsed ? 'p-2' : 'p-4'}`}>
          <button
            onClick={() => setCollapsed(c => !c)}
            className={`hidden md:flex items-center w-full rounded-xl transition-all duration-200 text-[#9e8b66] hover:text-[#5b4824] hover:bg-[#5b4824]/10 ${
              collapsed ? 'justify-center py-3' : 'gap-3 px-4 py-3'
            }`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg className={`w-5 h-5 flex-shrink-0 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
            {!collapsed && <span className="text-sm">Collapse</span>}
          </button>
          {!collapsed && (
            <div className="px-4 py-3 mt-2 rounded-xl bg-[#f7eede] border border-[#5b4824]/10">
              <div className="flex items-center gap-2 text-xs text-[#7a6b4e]">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
                Realtime services active
              </div>
            </div>
          )}
          {collapsed && (
            <div className="flex justify-center mt-2">
              <div className="w-2 h-2 rounded-full bg-success animate-pulse" title="Realtime services active" />
            </div>
          )}
        </div>
      </aside>

      <main className={`flex-1 ml-0 ${mainMargin} min-w-0 transition-all duration-300 ease-in-out`}>
        <header className="h-16 topbar-surface flex items-center justify-between px-4 md:px-8 sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 -ml-1 text-[#9e8b66] hover:text-[#5b4824] hover:bg-[#5b4824]/10 rounded-lg transition-colors md:hidden"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-[#b5a382]">Workspace</p>
              <h1 className="text-base md:text-lg font-bold text-[#3a2d14]">{activeLabel}</h1>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-3">
            <div className="badge badge-info">Live analytics</div>
            <div className="text-sm text-[#9e8b66]">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </div>
          </div>
        </header>

        <div className="content-wrap p-4 md:p-8 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
