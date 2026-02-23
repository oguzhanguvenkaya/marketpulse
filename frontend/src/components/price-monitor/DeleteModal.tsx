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
        <h3 className="text-lg font-semibold text-text-primary mb-4">
          {showDeleteModal === 'all' ? 'Delete All Products' : 'Delete Inactive Products'}
        </h3>
        <p className="text-text-body mb-6">
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
            className="btn-danger"
          >
            {deleteLoading ? 'Deleting...' : 'Yes, Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
