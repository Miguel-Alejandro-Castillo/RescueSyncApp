import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LOTE_ESTADOS } from "../../constants/lote";
import Toast from "../../components/Toast/Toast";
import styles from "./AdjudicarOfertas.module.css";
import { obtenerOfertasLote, obtenerLote } from "../../services/lotesService";
import { adjudicarOfertas } from "../../services/ofertasService";


function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function getAdjudicadoValue(value) {
  return Number.isFinite(value) ? value : 0;
}

function getOfferSummary(oferta) {
  const totalOfrecido = oferta.participantes.reduce(
    (acc, participante) => acc + (participante.ofrecido || 0),
    0,
  );
  const totalAdjudicado = oferta.participantes.reduce(
    (acc, participante) => acc + getAdjudicadoValue(participante.adjudicado),
    0,
  );

  return { totalOfrecido, totalAdjudicado };
}

function normalizeOferta(oferta) {
  const participantes = Array.isArray(oferta?.participantes)
    ? oferta.participantes.map((participante, index) => ({
        id: participante.id ?? `${oferta.id}-${participante.ong_id ?? index}`,
        nombre: participante.ong_name || `ONG #${participante.ong_id}`,
        ofrecido: participante.cantidad_aportada ?? 0,
        adjudicado: 0,
        ong_id: participante.ong_id,
      }))
    : [];

  return {
    id: oferta.id,
    tipo: oferta.tipo_oferta || (participantes.length <= 1 ? "INDIVIDUAL" : "CONSORCIO"),
    participantes,
  };
}

export default function AdjudicarOfertas() {
  const { idLote } = useParams();
 
  const navigate = useNavigate();
  const [lote, setLote] = useState(null);
  const [ofertas, setOfertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);

  const totalAdjudicado = ofertas.reduce(
    (acc, oferta) => acc + getOfferSummary(oferta).totalAdjudicado,
    0,
  );
  const cantidadRequerida = lote?.cantidad ?? 0;
  const diferencia = cantidadRequerida - totalAdjudicado;
  const restante = Math.max(diferencia, 0);
  const excedente = Math.max(totalAdjudicado - cantidadRequerida, 0);
  const progreso =
    cantidadRequerida > 0
      ? Math.min((totalAdjudicado / cantidadRequerida) * 100, 100)
      : 0;

  const actualizarParticipante = (ofertaId, participanteId, siguienteValor) => {
    setOfertas((actuales) => {
      const ofertaActual = actuales.find((oferta) => oferta.id === ofertaId);
      const participanteActual = ofertaActual?.participantes.find(
        (participante) => participante.id === participanteId,
      );

      if (!ofertaActual || !participanteActual) return actuales;

      const adjudicadoSinActual = actuales.reduce((acc, oferta) => {
        return (
          acc +
          oferta.participantes.reduce((subAcc, participante) => {
            if (oferta.id === ofertaId && participante.id === participanteId)
              return subAcc;
            return subAcc + getAdjudicadoValue(participante.adjudicado);
          }, 0)
        );
      }, 0);

      const maximoPermitido = Math.min(
        participanteActual.ofrecido,
        participanteActual.ofrecido +
          Math.max(
            cantidadRequerida - adjudicadoSinActual - participanteActual.ofrecido,
            0,
          ),
      );

      if (siguienteValor === "") {
        return actuales.map((oferta) => {
          if (oferta.id !== ofertaId) return oferta;

          return {
            ...oferta,
            participantes: oferta.participantes.map((participante) => {
              if (participante.id !== participanteId) return participante;
              return { ...participante, adjudicado: "" };
            }),
          };
        });
      }

      const normalizado = clamp(
        Number.isFinite(siguienteValor) ? siguienteValor : 0,
        0,
        maximoPermitido,
      );

      return actuales.map((oferta) => {
        if (oferta.id !== ofertaId) return oferta;

        return {
          ...oferta,
          participantes: oferta.participantes.map((participante) => {
            if (participante.id !== participanteId) return participante;
            return { ...participante, adjudicado: normalizado };
          }),
        };
      });
    });
  };

  const incrementar = (ofertaId, participante) => {
    const adjudicadoActual = getAdjudicadoValue(participante.adjudicado);
    actualizarParticipante(
      ofertaId,
      participante.id,
      adjudicadoActual + 1,
    );
  };

  const decrementar = (ofertaId, participante) => {
    const adjudicadoActual = getAdjudicadoValue(participante.adjudicado);
    actualizarParticipante(
      ofertaId,
      participante.id,
      adjudicadoActual - 1,
    );
  };

  const onInputChange = (ofertaId, participante, value) => {
    if (value === "") {
      actualizarParticipante(ofertaId, participante.id, "");
      return;
    }

    const parsed = Number.parseInt(value, 10);
    actualizarParticipante(
      ofertaId,
      participante.id,
      Number.isNaN(parsed) ? 0 : parsed,
    );
  };

  const confirmarAdjudicacion = async () => {
    if (totalAdjudicado === 0) {
      setToast({ type: "error", message: "No hay cantidades adjudicadas para confirmar." });
      return;
    }

    if (totalAdjudicado > cantidadRequerida) {
      setToast({ type: "error", message: "La cantidad adjudicada excede la cantidad requerida." });
      return;
    }

    try {
      setSaving(true);
      setToast(null);

      const adjudicaciones = ofertas
        .map((oferta) => ({
          detalles: oferta.participantes
            .map((participante) => ({
              participante_id: participante.id,
              cantidad_adjudicada: getAdjudicadoValue(participante.adjudicado),
            }))
            .filter((detalle) => detalle.cantidad_adjudicada > 0),
        }))
        .filter((adjudicacion) => adjudicacion.detalles.length > 0);

      await adjudicarOfertas(idLote, adjudicaciones);

      setToast({ type: "success", message: "La adjudicación se guardó correctamente." });
      window.setTimeout(() => {
        navigate(-1);
      }, 700);
    } catch (saveError) {
      setToast({
        type: "error",
        message: saveError.message || "No se pudo confirmar la adjudicación.",
      });
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    let active = true;

    const fetchData = async () => {
      try {
        setLoading(true);

        const [loteData, ofertasData] = await Promise.all([
          obtenerLote(idLote),
          obtenerOfertasLote(idLote),
        ]);

        if (!active) return;

        setLote(loteData);
        setOfertas(
          (Array.isArray(ofertasData) ? ofertasData : []).map(normalizeOferta),
        );
      } catch (fetchError) {
        if (!active) return;
        setToast({
          type: "error",
          message: fetchError.message || "No se pudieron cargar el lote y sus ofertas.",
        });
        setLote(null);
        setOfertas([]);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchData();

    return () => {
      active = false;
    };
  }, [idLote]);

  if (loading) {
    return (
      <div className={styles.page}>
        <Toast
          open={Boolean(toast)}
          type={toast?.type}
          message={toast?.message}
          onClose={() => setToast(null)}
        />
        <p>Cargando lote y ofertas...</p>
      </div>
    );
  }

  if (!lote) {
    return (
      <div className={styles.page}>
        <Toast
          open={Boolean(toast)}
          type={toast?.type}
          message={toast?.message}
          onClose={() => setToast(null)}
        />
        <p>No se encontró el lote solicitado.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Toast
        open={Boolean(toast)}
        type={toast?.type}
        message={toast?.message}
        onClose={() => setToast(null)}
      />
      {/* 
			<button type="button" className={styles.backButton} onClick={() => navigate(-1)}>
				← Volver a la emergencia
			</button>
     */}

      <div className={styles.hero}>
        <h1 className={styles.title}>Adjudicar ofertas</h1>
        <p className={styles.subtitle}>
          Distribuya la cobertura del lote entre ofertas individuales y
          consorcios antes de confirmar la adjudicación.
        </p>
      </div>

      <section className={styles.loteCard}>
        <div className={styles.loteHeader}>
          <div>
            <h3 className={styles.loteId}>Lote #{lote.id}</h3>
            <h3 className={styles.loteTitle}>
              {lote.tipoRecurso} - {lote.descripcion}
            </h3>
          </div>
          <span className={styles.loteBadge}>
            {(lote.estado || LOTE_ESTADOS.EN_ADJUDICACION).replace(/_/g, " ")}
          </span>
        </div>

        <div className={styles.panel}>
          <h3 className={styles.panelTitle}>Necesidad del lote</h3>
          <div className={styles.metrics}>
            <div>
              <span className={styles.metricLabel}>Requerido</span>
              <strong className={styles.metricValue}>{cantidadRequerida}</strong>
            </div>
            <div>
              <span className={styles.metricLabel}>Adjudicado</span>
              <strong className={styles.metricValue}>{totalAdjudicado}</strong>
            </div>
            <div>
              <span className={styles.metricLabel}>Restante</span>
              <strong className={styles.metricValue}>{restante}</strong>
            </div>
          </div>

          <div className={styles.progressBlock}>
            <div className={styles.progressTrack} aria-hidden="true">
              <div
                className={styles.progressFill}
                style={{ width: `${progreso}%` }}
              />
            </div>
            <span className={styles.progressText}>{Math.round(progreso)}%</span>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Ofertas</h2>
          <p className={styles.sectionHint}>
            Asigná unidades a cada participante sin superar lo ofrecido ni la
            necesidad restante.
          </p>
        </div>

        <div className={styles.offerList}>
          {ofertas.map((oferta) => {
            const { totalOfrecido, totalAdjudicado: adjudicadoOferta } =
              getOfferSummary(oferta);

            return (
              <article key={oferta.id} className={styles.offerCard}>
                <div className={styles.offerHeader}>
                  <div>
                    <h3 className={styles.offerTitle}>Oferta #{oferta.id}</h3>
                    <p className={styles.offerMeta}>
                      Total ofrecido: {totalOfrecido}
                    </p>
                  </div>
                  <span className={styles.offerType}>{oferta.tipo}</span>
                </div>

                <div className={styles.participantsBlock}>
                  <div className={styles.participantsHeadingRow}>
                    <span className={styles.participantsHeading}>
                      {oferta.tipo === "INDIVIDUAL"
                        ? "Participante"
                        : "Participantes"}
                    </span>
                  </div>

                  <div className={styles.participantsList}>
                    {oferta.participantes.map((participante) => (
                      <div
                        key={participante.id}
                        className={styles.participantRow}
                      >
                        <div className={styles.participantInfo}>
                          <strong className={styles.participantName}>
                            {participante.nombre}
                          </strong>
                          <span className={styles.participantOffer}>
                            Ofrece: {participante.ofrecido}
                          </span>
                        </div>

                        <div className={styles.stepper}>
                          <button
                            type="button"
                            className={styles.stepperButton}
                            onClick={() => decrementar(oferta.id, participante)}
                            disabled={getAdjudicadoValue(participante.adjudicado) <= 0}
                          >
                            −
                          </button>
                          <input
                            className={styles.stepperInput}
                            type="number"
                            min="0"
                            max={participante.ofrecido}
                            value={participante.adjudicado}
                            onChange={(event) =>
                              onInputChange(
                                oferta.id,
                                participante,
                                event.target.value,
                              )
                            }
                            aria-label={`Cantidad adjudicada a ${participante.nombre}`}
                          />
                          <button
                            type="button"
                            className={styles.stepperButton}
                            onClick={() => incrementar(oferta.id, participante)}
                            disabled={getAdjudicadoValue(participante.adjudicado) >= participante.ofrecido}
                          >
                            +
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className={styles.offerFooter}>
                  Adjudicado de esta oferta: <strong>{adjudicadoOferta}</strong>{" "}
                  / {totalOfrecido}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className={styles.summaryCard}>
        <h2 className={styles.summaryTitle}>Resumen de adjudicación</h2>

        <div className={styles.summaryGrid}>
          <div>
            <span>Requerido:</span>
            <strong>{cantidadRequerida}</strong>
          </div>
          <div>
            <span>Adjudicado:</span>
            <strong>{totalAdjudicado}</strong>
          </div>
          <div>
            <span>Restante:</span>
            <strong>{restante}</strong>
          </div>
        </div>

        <div className={styles.progressBlock}>
          <div className={styles.progressTrack} aria-hidden="true">
            <div
              className={styles.progressFill}
              style={{ width: `${progreso}%` }}
            />
          </div>
          <span className={styles.progressText}>{Math.round(progreso)}%</span>
        </div>

        <p
          className={
            excedente > 0
              ? styles.error
              : restante > 0
                ? styles.warning
                : styles.success
          }
        >
          {excedente > 0
            ? `Se adjudicaron ${excedente} unidades de más sobre lo requerido.`
            : restante > 0
              ? `Faltan ${restante} unidades para cubrir la necesidad`
              : "La necesidad del lote quedó completamente cubierta."}
        </p>

        <div className={styles.actions}>
          <button
            className={styles.secondaryAction}
            onClick={() => navigate(-1)}
            disabled={saving}
          >
            Cancelar
          </button>
          <button
            className={styles.primaryAction}
            onClick={confirmarAdjudicacion}
            disabled={saving || loading}
          >
            {saving ? "Confirmando..." : "Confirmar adjudicación"}
          </button>
        </div>
      </section>
    </div>
  );
}
