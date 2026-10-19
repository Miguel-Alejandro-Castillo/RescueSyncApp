import { useEffect } from "react";
import styles from "./Toast.module.css";

export default function Toast({
  open,
  type = "error",
  message,
  duration = 5000,
  onClose,
}) {
  useEffect(() => {
    if (!open || !duration || typeof onClose !== "function") return undefined;

    const timer = window.setTimeout(() => {
      onClose();
    }, duration);

    return () => window.clearTimeout(timer);
  }, [duration, onClose, open]);

  if (!open || !message) return null;

  return (
    <div className={`${styles.toast} ${styles[type] || styles.error}`} role="alert" aria-live="assertive">
      <div className={styles.content}>
        <strong className={styles.title}>
          {type === "success" ? "Éxito" : "Error"}
        </strong>
        <p className={styles.message}>{message}</p>
      </div>

      <button
        type="button"
        className={styles.closeButton}
        onClick={onClose}
        aria-label="Cerrar notificación"
      >
        ×
      </button>
    </div>
  );
}