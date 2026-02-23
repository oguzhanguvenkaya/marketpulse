import { useState, useEffect, useRef } from 'react';

export default function ApiKeyModal() {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = () => {
      setOpen(true);
      setKey('');
      setError('');
      setTimeout(() => inputRef.current?.focus(), 100);
    };
    window.addEventListener('mp:api-key-required', handler);
    return () => window.removeEventListener('mp:api-key-required', handler);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed) {
      setError('API key bos olamaz');
      return;
    }
    sessionStorage.setItem('mp_api_key', trimmed);
    window.dispatchEvent(new CustomEvent('mp:api-key-set', { detail: trimmed }));
    setOpen(false);
  };

  const handleCancel = () => {
    window.dispatchEvent(new CustomEvent('mp:api-key-set', { detail: null }));
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-[#162420] rounded-xl shadow-2xl p-6 w-full max-w-sm mx-4">
        <h2 className="text-lg font-semibold text-[#0f1419] dark:text-[#F0FDF4] mb-2">API Key Gerekli</h2>
        <p className="text-sm text-[#9e8b66] dark:text-[#6B8F80] mb-4">
          Bu islem icin API key girmeniz gerekiyor.
        </p>
        <form onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="password"
            value={key}
            onChange={(e) => { setKey(e.target.value); setError(''); }}
            placeholder="API key giriniz"
            className="w-full px-3 py-2 border border-[#e8dfcf] dark:border-[#2A4039] rounded-lg text-sm text-[#0f1419] dark:text-[#F0FDF4] focus:outline-none focus:ring-2 focus:ring-[#5f471d]/30 dark:focus:ring-[#4ADE80]/30 bg-[#fffbef] dark:bg-[#0F1A17] placeholder:text-[#9e8b66] dark:placeholder:text-[#6B8F80]"
          />
          {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 px-3 py-2 text-sm border border-[#e8dfcf] dark:border-[#2A4039] rounded-lg text-[#9e8b66] dark:text-[#6B8F80] hover:bg-[#f7eede] dark:hover:bg-[#1C2E28] transition-colors"
            >
              Iptal
            </button>
            <button
              type="submit"
              className="flex-1 px-3 py-2 text-sm bg-[#5f471d] dark:bg-[#4ADE80] text-white dark:text-[#0F1A17] rounded-lg hover:bg-[#3d3427] dark:hover:bg-[#4ADE80]/80 transition-colors font-medium"
            >
              Kaydet
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
