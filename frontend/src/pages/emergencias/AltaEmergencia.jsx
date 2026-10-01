import { useState } from "react";
import { Link } from "react-router-dom";
import { crearEmergencia } from "../../services/emergenciaService";
import styles from "./AltaEmergencia.module.css";
import ValidatedForm, { FieldError } from '../../components/ValidatedForm';
const initialFormData = {
  zonaAfectada: "",
  nivelGravedad: "medio",
  descripcionInicial: "",
};
export default function AltaEmergencia() {
  const [formData, setFormData] = useState(initialFormData);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  function handleChange(event) {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
    setFeedback(null);
  }
  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    if (!formData.zonaAfectada.trim() || !formData.descripcionInicial.trim()) {
      setFeedback({
        error: true,
        text: "Complete la zona y la descripción con información válida.",
      });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      await crearEmergencia({
        ...formData,
        zonaAfectada: formData.zonaAfectada.trim(),
        descripcionInicial: formData.descripcionInicial.trim(),
      });
      setFormData(initialFormData);
      setFeedback({ text: "Emergencia registrada correctamente." });
    } catch {
      setFeedback({
        error: true,
        text: "No pudimos registrar la emergencia. Revise la conexión e intente nuevamente.",
      });
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className={styles.page}>
      <div className="page-heading">
        <h1>Registrar una emergencia</h1>
        <p>
          Complete la información inicial para comenzar a coordinar la
          respuesta.
        </p>
      </div>
      <div className="panel">

        <ValidatedForm className="form-stack" onSubmit={handleSubmit} aria-busy={saving}>
          <fieldset disabled={saving} className="form-stack">
            <div>
              <label className="form-label" htmlFor="zona">
                Zona afectada
              </label>
              <input
                className="form-control"
                id="zona"
                name="zonaAfectada"
                data-required-message="Ingrese la zona afectada."
                maxLength={255}
                value={formData.zonaAfectada}
                onChange={handleChange}
                required
              />
              <FieldError name="zonaAfectada" />
            </div>
            <div>
              <label className="form-label" htmlFor="gravedad">
                Nivel de gravedad
              </label>
              <select
                className="form-select"
                id="gravedad"
                name="nivelGravedad"
                value={formData.nivelGravedad}
                onChange={handleChange}
                required
              >
                <option value="bajo">Bajo</option>
                <option value="medio">Medio</option>
                <option value="alto">Alto</option>
                <option value="critico">Crítico</option>
              </select>
              <FieldError name="nivelGravedad" />
            </div>
            <div>
              <label className="form-label" htmlFor="descripcion">
                Descripción inicial
              </label>
              <textarea
                className="form-control"
                id="descripcion"
                name="descripcionInicial"
                data-required-message="Ingrese una descripción de la emergencia."
                maxLength={500}
                rows="5"
                value={formData.descripcionInicial}
                onChange={handleChange}
                required
              />
              <FieldError name="descripcionInicial" />
            </div>
          </fieldset>
          {feedback && (
            <div
              className={"notice" + (feedback.error ? " notice-error" : "")}
              role={feedback.error ? "alert" : "status"}
            >
              {feedback.text}
            </div>
          )}
          <div className="form-actions">
            <Link className="btn btn-outline-secondary" to="/dashboard">
              Volver al inicio
            </Link>
            <button className="btn btn-primary" disabled={saving} type="submit">
              {saving ? "Guardando…" : "Registrar emergencia"}
            </button>
          </div>
        </ValidatedForm>
      </div>
    </div>
  );
}
