import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { obtenerLotes } from "../../services/emergenciaService";
import { LOTE_ESTADOS, normalizeEstadoLote } from "../../constants/lote";
import styles from "./VerLotes.module.css";

const getEstadoStyle = (estado) => {
  const base = {
    padding: "0.4rem 0.8rem",
    borderRadius: "0.6rem",
    fontWeight: "700",
    fontSize: "0.8rem"
  };

  switch ((estado || "").toLowerCase()) {
    case LOTE_ESTADOS.CREADO:
      return { ...base, backgroundColor: "#fff3cd", color: "#856404" };
    case LOTE_ESTADOS.ACTIVO:
    case LOTE_ESTADOS.ABIERTO:
      return { ...base, backgroundColor: "#d1f2eb", color: "#0f766e" };
    case LOTE_ESTADOS.CUBIERTO:
      return { ...base, backgroundColor: "#e2e8f0", color: "#334155" };
    case LOTE_ESTADOS.REFORMULADO:
      return { ...base, backgroundColor: "#f3e8ff", color: "#7e22ce" };
    default:
      return { ...base, backgroundColor: "#e9ecef", color: "#495057" };
  }
};

export default function VerLotes() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [lotes, setLotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLotes = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await obtenerLotes(id);
      setLotes(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLotes();
  }, [id]);

  return (
    <div className={styles.page} style={{ padding: "2rem", maxWidth: "900px", margin: "0 auto" }}>
      {error && (
        <div className="notice notice-error" role="alert" style={{ marginBottom: "1rem" }}>
          <strong>No se pudo completar la acción</strong>
          <p>{error}</p>
        </div>
      )}

      <button
        onClick={() => navigate(-1)}
        style={{ marginBottom: "1.5rem", cursor: "pointer", padding: "0.5rem 1rem", borderRadius: "0.5rem", border: "1px solid var(--border)" }}
      >
        ← Volver
      </button>

      <div className="page-heading">
        <h1>Lotes de la Emergencia #{id}</h1>
        <p>Listado de lotes asociados a esta emergencia.</p>
      </div>

      {loading ? (
        <p>Cargando lotes...</p>
      ) : lotes.length === 0 ? (
        <p>No se encontraron lotes para esta emergencia.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {lotes.map((lote) => {
            const cantCubierta = lote.cantidadCubierta || 0;
            const faltante = Math.max((lote.cantidad || 0) - cantCubierta, 0);

            return (
              <article
                key={lote.id}
                className={styles.card}
                style={{ border: "1px solid var(--border)", padding: "1.2rem", borderRadius: "12px", backgroundColor: "var(--surface)" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h2 className={styles.title} style={{ marginBottom: "0.4rem" }}>
                      Lote #{lote.id}
                    </h2>
                    <p style={{ color: "var(--muted)", margin: 0 }}>
                      {lote.tipoRecurso} - {lote.descripcion}
                    </p>
                    <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "0.8rem", flexWrap: "wrap" }}>
                      <span style={getEstadoStyle(lote.estado)}>
                        Estado: {normalizeEstadoLote(lote.estado)}
                      </span>
                      <span style={{ padding: "0.4rem 0.8rem", borderRadius: "0.6rem", fontWeight: "700", fontSize: "0.8rem", backgroundColor: "#f8fafc", color: "#334155" }}>
                        Cantidad requerida: {lote.cantidad}
                      </span>

                      <button
                          className={styles.submit}
                          onClick={() =>
                            navigate(`/emergencias/propias/${id}/lotes/${lote.id}/adjudicar-ofertas`)
                          }
                          hidden={lote.estado !== LOTE_ESTADOS.EN_ADJUDICACION}
                        >
                          Adjudicar ofertas
                    </button>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
