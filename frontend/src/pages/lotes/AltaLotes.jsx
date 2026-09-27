import React, { useState } from "react";
import { crearLotes } from "../../services/lotesService";
import styles from "./AltaLotes.module.css";

// Datos simulados de emergencias pendientes
const MOCK_EMERGENCIAS_PENDIENTES = [
  {
    id: "EMG-101",
    zonaAfectada: "Municipio de Quilmes - Sector Este",
    nivelGravedad: "critico",
    descripcionInicial:
      "Inundación por desborde de arroyo. Se requieren refugios y atención médica urgente.",
    tiempoVentanaSugerido: 2, // horas
  },
  {
    id: "EMG-102",
    zonaAfectada: "Zona Norte - Tigre",
    nivelGravedad: "alto",
    descripcionInicial:
      "Temporal de viento y lluvia con caída de postes de luz y anegamientos.",
    tiempoVentanaSugerido: 6, // horas
  },
  {
    id: "EMG-103",
    zonaAfectada: "La Plata - Casco Urbano",
    nivelGravedad: "medio",
    descripcionInicial:
      "Anegamiento puntual de avenidas principales sin evacuados de gravedad.",
    tiempoVentanaSugerido: 12, // horas
  },
];

const AltaLotes = () => {
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [emergenciaSeleccionada, setEmergenciaSeleccionada] = useState(null);
  const [horasVentana, setHorasVentana] = useState(2); // Estado editable de la ventana de tiempo
  const [lotes, setLotes] = useState([
    { tipoRecurso: "Insumos", descripcion: "", cantidad: 1 },
  ]);

  const handleEmergenciaChange = (e) => {
    const id = e.target.value;
    const encontrada = MOCK_EMERGENCIAS_PENDIENTES.find(
      (item) => item.id === id,
    );
    setEmergenciaSeleccionada(encontrada || null);
    if (encontrada) {
      setHorasVentana(encontrada.tiempoVentanaSugerido); // Precarga el valor sugerido
    }
  };

  const handleLoteChange = (index, e) => {
    const { name, value } = e.target;
    const nuevosLotes = lotes.map((lote, i) =>
      i === index ? { ...lote, [name]: value } : lote,
    );
    setLotes(nuevosLotes);
  };

  const handleAddLote = () => {
    setLotes([
      ...lotes,
      { tipoRecurso: "Insumos", descripcion: "", cantidad: 1 },
    ]);
  };

  const handleRemoveLote = (index) => {
    if (lotes.length === 1) return;
    const nuevosLotes = lotes.filter((_, i) => i !== index);
    setLotes(nuevosLotes);
  };

  const getBadgeGravedad = (gravedad) => {
    switch (gravedad) {
      case "critico":
        return <span className="badge bg-danger">Gravedad: CRÍTICA</span>;
      case "alto":
        return (
          <span className="badge bg-warning text-dark">Gravedad: ALTA</span>
        );
      case "medio":
        return <span className="badge bg-info text-dark">Gravedad: MEDIA</span>;
      default:
        return <span className="badge bg-secondary">Gravedad: BAJA</span>;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!emergenciaSeleccionada || saving) return;
    if (lotes.some((lote) => !lote.descripcion.trim())) {
      setFeedback({
        error: true,
        text: "Completá la descripción de cada lote.",
      });
      return;
    }

    const payload = {
      emergenciaId: emergenciaSeleccionada.id,
      duracionConvocatoriaHoras: Number(horasVentana),
      lotes: lotes.map((lote) => ({
        ...lote,
        descripcion: lote.descripcion.trim(),
        cantidad: Number(lote.cantidad),
      })),
    };

    setSaving(true);
    setFeedback(null);
    try {
      await crearLotes(payload);
      setFeedback({
        text: "Simulación completada. Los lotes no se publicaron en un servidor.",
      });
    } catch {
      setFeedback({
        error: true,
        text: "No pudimos completar la operación. Intentá nuevamente.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className="page-heading">
        <h1>Lotes y convocatorias</h1>
        <p>
          Organizá la ayuda necesaria para cada emergencia y definí el plazo de
          participación.
        </p>
      </div>
      <div className="row justify-content-center">
        <div className="col-12">
          <div className="panel">
            <div className="">
              <h2 className="h5 mb-4">Preparar convocatoria</h2>

              <form
                onSubmit={handleSubmit}
                onChange={() => setFeedback(null)}
                aria-busy={saving}
              >
                <fieldset disabled={saving}>
                  {/* SELECCIÓN DE EMERGENCIA */}
                  <div className="mb-4">
                    <label htmlFor="emergencia" className="form-label fw-bold">
                      Emergencia
                    </label>
                    <select
                      id="emergencia"
                      className="form-select"
                      value={
                        emergenciaSeleccionada ? emergenciaSeleccionada.id : ""
                      }
                      onChange={handleEmergenciaChange}
                      required
                    >
                      <option value="">
                        -- Seleccione una emergencia --
                      </option>
                      {MOCK_EMERGENCIAS_PENDIENTES.map((emg) => (
                        <option key={emg.id} value={emg.id}>
                          [{emg.id}] {emg.zonaAfectada} (
                          {emg.nivelGravedad.toUpperCase()})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* RESUMEN DE LA EMERGENCIA Y CAMPO EDITABLE DE DURACIÓN */}
                  {emergenciaSeleccionada && (
                    <div className={styles.summary}>
                      <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-2">
                        <h6 className="mb-0 fw-bold text-body">
                          Zona: {emergenciaSeleccionada.zonaAfectada}
                        </h6>
                        {getBadgeGravedad(emergenciaSeleccionada.nivelGravedad)}
                      </div>
                      <p className="small text-muted mb-3">
                        {emergenciaSeleccionada.descripcionInicial}
                      </p>
                      <div className="row align-items-center g-2 pt-2 border-top">
                        <div className="col-md-7">
                          <label htmlFor="horas" className="form-label mb-0 fw-bold small">
                            Duración de la Convocatoria para ONGs (Horas):
                          </label>
                          <div id="duration-suggestion" className="text-muted small">
                            Sugerido por gravedad ({emergenciaSeleccionada.nivelGravedad}): {emergenciaSeleccionada.tiempoVentanaSugerido} hs.
                          </div>
                        </div>
                        <div className="col-md-5">
                          <input
                            id="horas"
                            step="1"
                            type="number"
                            className="form-control"
                            min="1"
                            max="72"
                            value={horasVentana}
                            onChange={(e) => setHorasVentana(e.target.value)}
                            aria-describedby="duration-suggestion"
                            required
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <hr className="my-4" />

                  {/* DESGLOSE DE LOTES */}
                  <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-3">
                    <h5 className="mb-0">Lotes de Recursos Requeridos</h5>
                    <button
                      type="button"
                      className="btn btn-outline-success btn-sm"
                      onClick={handleAddLote}
                      disabled={!emergenciaSeleccionada}
                    >
                      + Agregar otro lote
                    </button>
                  </div>

                  {lotes.map((lote, index) => (
                    <div
                      key={index}
                      className={styles.lote}
                    >
                      <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-2">
                        <span className="badge bg-secondary">
                          Lote #{index + 1}
                        </span>
                        {lotes.length > 1 && (
                          <button
                            type="button"
                            className="btn btn-outline-danger btn-sm border-0"
                            onClick={() => handleRemoveLote(index)}
                          >
                            Eliminar
                          </button>
                        )}
                      </div>

                      <div className="row g-2">
                        <div className="col-md-3">
                          <label
                            htmlFor={`tipo-${index}`}
                            className="form-label small"
                          >
                            Tipo de recurso
                          </label>
                          <select
                            className="form-select form-select-sm"
                            id={`tipo-${index}`}
                            name="tipoRecurso"
                            value={lote.tipoRecurso}
                            onChange={(e) => handleLoteChange(index, e)}
                            required
                          >
                            <option value="Insumos">Insumos / Alimentos</option>
                            <option value="Personal">
                              Personal / Voluntarios
                            </option>
                            <option value="Maquinaria">
                              Maquinaria / Vehículos
                            </option>
                            <option value="Refugio">Refugio / Abrigo</option>
                          </select>
                        </div>

                        <div className="col-md-6">
                          <label
                            htmlFor={`descripcion-${index}`}
                            className="form-label small"
                          >
                            Recurso
                          </label>
                          <input
                            type="text"
                            className="form-control form-control-sm"
                            id={`descripcion-${index}`}
                            name="descripcion"
                            placeholder="Ej. Botella de agua potable 2L"
                            value={lote.descripcion}
                            onChange={(e) => handleLoteChange(index, e)}
                            required
                          />
                        </div>

                        <div className="col-md-3">
                          <label
                            htmlFor={`cantidad-${index}`}
                            className="form-label small"
                          >
                            Cantidad requerida
                          </label>
                          <input
                            type="number"
                            className="form-control form-control-sm"
                            id={`cantidad-${index}`}
                            name="cantidad"
                            step="1"
                            min="1"
                            value={lote.cantidad}
                            onChange={(e) => handleLoteChange(index, e)}
                            required
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* BOTÓN DE ACCIÓN */}
                  <div className="d-grid mt-4">
                    <button
                      type="submit"
                      className="btn btn-primary btn-lg"
                      disabled={!emergenciaSeleccionada}
                    >
                      {saving
                        ? "Publicando…"
                        : "Publicar convocatoria"}
                    </button>
                  </div>
                </fieldset>
                {feedback && (
                  <div
                    className={`notice mt-3${feedback.error ? " notice-error" : ""}`}
                    role={feedback.error ? "alert" : "status"}
                  >
                    {feedback.text}
                  </div>
                )}
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AltaLotes;
