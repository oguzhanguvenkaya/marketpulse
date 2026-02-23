import { usePriceMonitor } from '../hooks/usePriceMonitor';
import PriceMonitorFilters from '../components/price-monitor/PriceMonitorFilters';
import FetchTaskProgress from '../components/price-monitor/FetchTaskProgress';
import MonitoredProductList from '../components/price-monitor/MonitoredProductList';
import SellerDetailPanel from '../components/price-monitor/SellerDetailPanel';
import ImportModal from '../components/price-monitor/ImportModal';
import DeleteModal from '../components/price-monitor/DeleteModal';
import ConfirmDialog from '../components/ConfirmDialog';

export default function PriceMonitor() {
  const pm = usePriceMonitor();

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      <PriceMonitorFilters {...pm} />

      {pm.fetchTaskId && <FetchTaskProgress {...pm} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MonitoredProductList {...pm} />
        <SellerDetailPanel {...pm} />
      </div>

      {pm.showImportModal && <ImportModal {...pm} />}
      {pm.showDeleteModal && <DeleteModal {...pm} />}

      <ConfirmDialog
        open={pm.deleteTarget !== null}
        title="Urunu Sil"
        message="Bu urunu silmek istediginizden emin misiniz?"
        confirmLabel="Sil"
        cancelLabel="Iptal"
        variant="danger"
        onConfirm={pm.handleDeleteConfirm}
        onCancel={pm.handleDeleteCancel}
      />
    </div>
  );
}
