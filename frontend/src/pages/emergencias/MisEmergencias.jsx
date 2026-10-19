import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getSession, getSessionUserId } from "../../services/authService";
import { obtenerEmergencias } from "../../services/emergenciaService";
import { EMERGENCIA_ESTADOS } from "../../constants/emergencia";
import { NIVELES_GRAVEDAD, getNivelGravedadLabel, normalizeNivelGravedad } from "../../constants/gravedad";
import styles from "./MisEmergencias.module.css";

const getStyleSinLotes = () => {
  return {
    padding: "0.4rem 0.8rem",
    borderRadius: "0.6rem",
    fontWeight: "700",
    fontSize: "0.8rem",
    backgroundColor: "#e9ecef",
    color: "#495057",
  };
};

const getEstadoStyle = (estado) => {
  const base = {
    padding: "0.4rem 0.8rem",
    borderRadius: "0.6rem",
    fontWeight: "700",
    fontSize: "0.8rem",
    textTransform: "capitalize",
  };

  switch ((estado || "").toLowerCase()) {
    case EMERGENCIA_ESTADOS.PUBLICADA:
      return { ...base, backgroundColor: "#d1f2eb", color: "#0f766e" };
    case EMERGENCIA_ESTADOS.CREADA:
      return { ...base, backgroundColor: "#fff3cd", color: "#856404" };
    case EMERGENCIA_ESTADOS.CONVOCATORIA_CERRADA:
      return { ...base, backgroundColor: "#e2e8f0", color: "#334155" };
    default:
      return { ...base, backgroundColor: "#e9ecef", color: "#495057" };
  }
};

const getNivelStyle = (nivel) => {
  const base = {
    padding: "0.4rem 0.8rem",
    borderRadius: "0.6rem",
    fontWeight: "700",
    fontSize: "0.8rem",
  };

  switch (normalizeNivelGravedad(nivel)) {
    case NIVELES_GRAVEDAD.ALTO:
    case NIVELES_GRAVEDAD.CRITICO:
      return { ...base, backgroundColor: "#ffe5e5", color: "#d90429" };
    case NIVELES_GRAVEDAD.MEDIO:
      return { ...base, backgroundColor: "#fff3cd", color: "#856404" };
    case NIVELES_GRAVEDAD.BAJO:
      return { ...base, backgroundColor: "#d1fae5", color: "#065f46" };
    default:
      return { ...base, backgroundColor: "#e9ecef", color: "#495057" };
  }
};

export default function MisEmergencias() {
  const [emergencias, setEmergencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchEmergencias = async () => {
    try {
      setLoading(true);
      setError(null);

      const session = getSession();
      const usuarioCreador = getSessionUserId(session);

      if (!usuarioCreador) {
        setEmergencias([]);
        return;
      }

      const data = await obtenerEmergencias(usuarioCreador);
      setEmergencias(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmergencias();
  }, []);

  if (loading) {
    return (
      <div className={styles.page}>
        <div style={{ maxWidth: "900px", margin: "0 auto" }}>
          Cargando emergencias...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div style={{ maxWidth: "900px", margin: "0 auto" }}>
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div
        style={{
          maxWidth: "900px",
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          gap: "2rem",
        }}
      >
        {emergencias.length === 0 ? (
          <div className={styles.card}>
            <div className={styles.cardBody}>
              <p style={{ margin: 0 }}>
                Todavía no creaste ninguna emergencia.
              </p>
            </div>
          </div>
        ) : (
          emergencias.map((emergencia) => {
            return (
              <div key={emergencia.id} className={styles.card}>
                <div className={styles.cardBody}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                      gap: "1rem",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <h2
                        className={styles.title}
                        style={{ marginBottom: "0.4rem" }}
                      >
                        Emergencia #{emergencia.id} - {emergencia.zonaAfectada}
                      </h2>
                      <p style={{ color: "var(--muted)", margin: 0 }}>
                        {emergencia.descripcionInicial}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "1rem",
                          marginTop: "0.4rem",
                          flexWrap: "wrap",
                        }}
                      >
                        <span style={getNivelStyle(emergencia.nivelGravedad)}>
                          Gravedad: {getNivelGravedadLabel(emergencia.nivelGravedad)}
                        </span>
                        <span
                          style={getEstadoStyle(emergencia.estado)}
                        >
                          Estado: {emergencia.estado}
                        </span>
                        {/* no mostrar este boton si el estado de la emergencia es "creado" */}
                        <button
                          className={styles.submit}
                          onClick={() =>
                            navigate(`/emergencias/propias/${emergencia.id}/lotes`)
                          }
                          hidden={emergencia.estado === EMERGENCIA_ESTADOS.CREADA}
                        >
                          Ver lotes
                        </button>
                        <span style={getStyleSinLotes()}
                          hidden={emergencia.estado !== EMERGENCIA_ESTADOS.CREADA}
                        >
                          Sin Lotes
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
