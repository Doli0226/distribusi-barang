import Modal from "@/components/ui/Modal";

export default function Confirm({ open, title = "Konfirmasi", message, onClose, onConfirm, danger, confirmLabel = "Lanjutkan" }) {
  if (!open) return null;
  return (
    <Modal onClose={onClose} eyebrow="KONFIRMASI" title={title} testid="confirm-modal">
      <div className="confirm-modal">
        <p>{message}</p>
        <div className="modal-actions">
          <button className="outline-button" onClick={onClose} data-testid="confirm-cancel">Batal</button>
          <button
            className="primary-button"
            style={danger ? { background: "#dc2626", boxShadow: "0 3px 8px #dc262640" } : {}}
            onClick={onConfirm}
            data-testid="confirm-ok"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
