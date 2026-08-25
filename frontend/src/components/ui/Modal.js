import { X } from "lucide-react";
import { useEffect } from "react";

export default function Modal({ children, onClose, title, subtitle, eyebrow, wide, testid }) {
  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose} data-testid={testid || "modal-backdrop"}>
      <div className={`modal ${wide ? "wide" : ""}`} onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} data-testid="modal-close-button"><X size={18} /></button>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        {title && <h2>{title}</h2>}
        {subtitle && <p className="subtitle">{subtitle}</p>}
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
