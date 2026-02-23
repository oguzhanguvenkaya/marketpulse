import { useState, useEffect } from 'react';
import { createSearchTask, getSearchTask, getTasks, getStats, getStatTrends } from '../services/api';
import type { SearchTask, Stats, StatTrends } from '../services/api';
import Sparkline, { TrendIndicator } from '../components/Sparkline';

export default function Dashboard() {
  const [keyword, setKeyword] = useState('');
  const [platform, setPlatform] = useState('hepsiburada');
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<SearchTask[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [trends, setTrends] = useState<StatTrends | null>(null);
  const [currentTask, setCurrentTask] = useState<SearchTask | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (currentTask && currentTask.status === 'running') {
      interval = setInterval(async () => {
        const updated = await getSearchTask(currentTask.id);
        setCurrentTask(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          loadData();
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [currentTask]);

  const loadData = async () => {
    try {
      const [tasksData, statsData, trendsData] = await Promise.all([
        getTasks(10),
        getStats(),
        getStatTrends(),
      ]);
      setTasks(tasksData);
      setStats(statsData);
      setTrends(trendsData);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim()) return;
    
    setLoading(true);
    try {
      const task = await createSearchTask(keyword, platform);
      setCurrentTask(task);
      setKeyword('');
    } catch (error) {
      console.error('Error creating task:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'badge-warning',
      running: 'badge-info',
      completed: 'badge-success',
      failed: 'badge-danger',
    };
    return (
      <span className={`badge ${styles[status] || 'badge-neutral'}`}>
        {status}
      </span>
    );
  };

  const statCards = [
    { label: 'Total Products', value: stats?.total_products || 0, color: '#1e9df1', trendKey: 'products' as const, icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
    )},
    { label: 'Data Points', value: stats?.total_snapshots || 0, color: '#22c55e', trendKey: 'snapshots' as const, icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
      </svg>
    )},
    { label: 'Total Searches', value: stats?.total_tasks || 0, color: '#f7b928', trendKey: 'tasks' as const, icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    )},
    { label: 'Completed', value: stats?.completed_tasks || 0, color: '#f59e0b', trendKey: 'completed' as const, icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )},
  ];

  return (
    <div className="space-y-5 md:space-y-6 animate-fade-in">
      <div className="mb-2 md:mb-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-[#0f1419] dark:text-[#F0FDF4]">Dashboard</h1>
          <p className="text-sm md:text-base text-[#9e8b66] dark:text-[#6B8F80] mt-1">Monitor marketplace data and analytics</p>
        </div>
      </div>

      <div className="card-dark p-4 md:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-[#0f1419] dark:text-[#F0FDF4]">Keyword Search</h2>
        </div>
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3 md:gap-4">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Enter keyword to search..."
            className="input-dark flex-1"
          />
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="input-dark w-full md:w-auto md:min-w-[180px]"
          >
            <option value="hepsiburada">Hepsiburada</option>
            <option value="trendyol" disabled>Trendyol (Soon)</option>
            <option value="amazon" disabled>Amazon (Soon)</option>
          </select>
          <button
            type="submit"
            disabled={loading || !keyword.trim()}
            className="btn-primary w-full md:w-auto flex items-center justify-center"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Searching...
              </span>
            ) : 'Search'}
          </button>
        </form>
        
        {currentTask && (
          <div className="mt-4 p-3 md:p-4 rounded-lg bg-accent-primary/5 border border-accent-primary/20">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex items-start md:items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
                <span className="text-sm md:text-base text-[#0f1419] dark:text-[#F0FDF4]">Searching for "<span className="text-accent-primary">{currentTask.keyword}</span>"</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 md:gap-3">
                {getStatusBadge(currentTask.status)}
                {currentTask.status === 'completed' && (
                  <span className="text-xs md:text-sm text-[#9e8b66] dark:text-[#6B8F80]">{currentTask.total_products} products found</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {statCards.map((stat, index) => (
          <div
            key={index}
            className="stat-card"
            style={{ '--stat-color': stat.color } as React.CSSProperties}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="text-2xl md:text-3xl font-bold mb-1" style={{ color: stat.color }}>
                    {stat.value.toLocaleString()}
                  </div>
                  {trends && <TrendIndicator data={trends[stat.trendKey]} />}
                </div>
                <div className="text-xs md:text-sm text-[#9e8b66] dark:text-[#6B8F80]">{stat.label}</div>
              </div>
              <div className="p-2 rounded-lg" style={{ backgroundColor: `${stat.color}15` }}>
                <span style={{ color: stat.color }}>{stat.icon}</span>
              </div>
            </div>
            {trends && trends[stat.trendKey] && (
              <div className="mt-3">
                <Sparkline data={trends[stat.trendKey]} color={stat.color} />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card-dark overflow-hidden">
        <div className="px-4 md:px-6 py-3 md:py-4 border-b border-[#5b4824]/8 dark:border-[#4ADE80]/8 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-[#0f1419] dark:text-[#F0FDF4]">Recent Searches</h2>
        </div>
        <div className="divide-y divide-[#5b4824]/8 dark:divide-[#4ADE80]/8">
          {tasks.length === 0 ? (
            <div className="px-4 md:px-6 py-10 md:py-12 text-center">
              <div className="w-12 h-12 rounded-full bg-[#f0e8d8] dark:bg-[#1C2E28] flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <p className="text-[#9e8b66] dark:text-[#6B8F80]">No searches yet</p>
              <p className="text-sm text-neutral-500 mt-1">Start by entering a keyword above</p>
            </div>
          ) : (
            tasks.map((task, index) => (
              <div 
                key={task.id} 
                className="px-4 md:px-6 py-3 md:py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:bg-[#5b4824]/[0.03] dark:hover:bg-[#4ADE80]/[0.03] transition-colors"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-center gap-4">
                  <div className="w-9 h-9 md:w-10 md:h-10 rounded-lg bg-[#f0e8d8] dark:bg-[#1C2E28] flex items-center justify-center">
                    <svg className="w-5 h-5 text-[#9e8b66] dark:text-[#6B8F80]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <div className="min-w-0">
                    <div className="font-medium text-[#0f1419] dark:text-[#F0FDF4] truncate">{task.keyword}</div>
                    <div className="text-xs md:text-sm text-neutral-500 flex items-center gap-2">
                      <span className="capitalize">{task.platform}</span>
                      <span className="text-[#b5a382] dark:text-[#6B8F80]">•</span>
                      <span>{new Date(task.created_at).toLocaleString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto">
                  <span className="text-xs md:text-sm text-[#9e8b66] dark:text-[#6B8F80]">{task.total_products} products</span>
                  {getStatusBadge(task.status)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
