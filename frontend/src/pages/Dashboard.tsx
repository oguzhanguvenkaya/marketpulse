import { useState, useEffect } from 'react';
import { createSearchTask, getSearchTask, getTasks, getStats } from '../services/api';
import type { SearchTask, Stats } from '../services/api';

export default function Dashboard() {
  const [keyword, setKeyword] = useState('');
  const [platform, setPlatform] = useState('hepsiburada');
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<SearchTask[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
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
      const [tasksData, statsData] = await Promise.all([getTasks(10), getStats()]);
      setTasks(tasksData);
      setStats(statsData);
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
      pending: 'bg-yellow-100 text-yellow-800',
      running: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4">🔍 Anahtar Kelime Araması</h2>
        <form onSubmit={handleSearch} className="flex gap-4">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Anahtar kelime girin..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="hepsiburada">Hepsiburada</option>
            <option value="trendyol" disabled>Trendyol (Yakında)</option>
            <option value="amazon" disabled>Amazon (Yakında)</option>
          </select>
          <button
            type="submit"
            disabled={loading || !keyword.trim()}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Aranıyor...' : 'Ara'}
          </button>
        </form>
        
        {currentTask && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-medium">"{currentTask.keyword}"</span> için arama
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(currentTask.status)}
                {currentTask.status === 'completed' && (
                  <span className="text-sm text-gray-600">{currentTask.total_products} ürün bulundu</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-indigo-600">{stats?.total_products || 0}</div>
          <div className="text-gray-500">Toplam Ürün</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-green-600">{stats?.total_snapshots || 0}</div>
          <div className="text-gray-500">Veri Noktası</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-blue-600">{stats?.total_tasks || 0}</div>
          <div className="text-gray-500">Toplam Arama</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-purple-600">{stats?.completed_tasks || 0}</div>
          <div className="text-gray-500">Tamamlanan</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">📋 Son Aramalar</h2>
        </div>
        <div className="divide-y">
          {tasks.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              Henüz arama yapılmadı
            </div>
          ) : (
            tasks.map((task) => (
              <div key={task.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <div className="font-medium">{task.keyword}</div>
                  <div className="text-sm text-gray-500">{task.platform} • {new Date(task.created_at).toLocaleString('tr-TR')}</div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600">{task.total_products} ürün</span>
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
