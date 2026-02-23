import type { UsePriceMonitorReturn } from '../../hooks/usePriceMonitor';

export default function DeleteModal({
  showDeleteModal,
  setShowDeleteModal,
  totalProducts,
  inactiveTotalCount,
  platform,
  deleteLoading,
  handleBulkDelete,
}: UsePriceMonitorReturn) {
  if (!showDeleteModal) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card-dark p-5 md:p-6 max-w-md w-full mx-auto border border-red-500/30">
        <h3 className="text-lg font-semibold text-[#0f1419] mb-4">
          {showDeleteModal === 'all' ? 'Delete All Products' : 'Delete Inactive Products'}
        </h3>
        <p className="text-[#5f471d] mb-6">
          {showDeleteModal === 'all'
            ? `Are you sure you want to delete all ${totalProducts} products for ${platform}? This action cannot be undone.`
            : `Are you sure you want to delete ${inactiveTotalCount} inactive products for ${platform}? This action cannot be undone.`
          }
        </p>
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
          <button
            onClick={() => setShowDeleteModal(null)}
            disabled={deleteLoading}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleBulkDelete}
            disabled={deleteLoading}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-[#0f1419] font-medium transition-colors disabled:opacity-50"
          >
            {deleteLoading ? 'Deleting...' : 'Yes, Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
