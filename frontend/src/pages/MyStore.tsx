import { useMyStore } from '../hooks/useMyStore';
import MyStoreHeader from '../components/my-store/MyStoreHeader';
import MyStoreProductList from '../components/my-store/MyStoreProductList';
import MyStoreDetailPanel from '../components/my-store/MyStoreDetailPanel';
import MyStoreImportModal from '../components/my-store/MyStoreImportModal';
import MyStorePlatformDrawer from '../components/my-store/MyStorePlatformDrawer';

export default function MyStore() {
  const ms = useMyStore();

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      <MyStoreHeader {...ms} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MyStoreProductList {...ms} />
        <MyStoreDetailPanel {...ms} />
      </div>

      {ms.showImportModal && <MyStoreImportModal {...ms} />}
      <MyStorePlatformDrawer {...ms} />

      {/* Delete All Confirmation Modal */}
      {ms.showDeleteAllModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="card-dark rounded-2xl shadow-2xl max-w-sm w-full p-6 border border-[var(--surface-border)]">
            <h3 className="text-lg font-semibold text-text-primary mb-2">Tüm Ürünleri Sil</h3>
            <p className="text-sm text-text-muted mb-4">
              Tüm web ürünleri silinecek. Bu işlem geri alınamaz.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => ms.setShowDeleteAllModal(false)} className="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-hover">
                İptal
              </button>
              <button onClick={ms.handleDeleteAll} className="px-4 py-2 rounded-lg text-sm font-medium bg-danger text-white hover:bg-danger/80">
                Sil
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
