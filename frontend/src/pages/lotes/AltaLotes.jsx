import styles from './AltaLotes.module.css';
import ValidatedForm, { FieldError } from '../../components/ValidatedForm';
import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import SeleccionarEmergencia from './SeleccionarEmergencia';
import { obtenerEmergenciaPorId, crearLotes, decidirEmergencia } from '../../services/lotesService';
import { obtenerLotes } from '../../services/emergenciaService';
import { EMERGENCIA_ESTADOS } from '../../constants/emergencia';
import { NIVELES_GRAVEDAD, getNivelGravedadLabel, normalizeNivelGravedad } from '../../constants/gravedad';
import { RECURSOS_POR_TIPO, TIPOS_RECURSOS } from '../../constants/lote';

export default function AltaLotes() {
    const [params] = useSearchParams();
    const id = params.get('emergenciaId');
    return id ? <FormularioLotes key={id} /> : <SeleccionarEmergencia />;
}

const FormularioLotes = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const emergenciaId = searchParams.get('emergenciaId');
    // Ids de los lotes que el coordinador decidió reformular desde "Evaluar emergencias"
    const lotesAReformular = (searchParams.get('reformular') || '').split(',').filter(Boolean).map(Number);
    const reformulando = lotesAReformular.length > 0;

    const [emergenciaSeleccionada, setEmergenciaSeleccionada] = useState(null);
    const [lotesReemplazados, setLotesReemplazados] = useState([]);
    const [loadingEmergencia, setLoadingEmergencia] = useState(false);
    const [error, setError] = useState('');
    const [saving, setSaving] = useState(false);
    const [submitError, setSubmitError] = useState('');

    const [lotes, setLotes] = useState([
        { 
            tipoRecurso: 'Insumos', 
            descripcion: RECURSOS_POR_TIPO['Insumos']?.[0] || 'Raciones de comida', 
            cantidad: 1 
        }
    ]);

    const handleTipoRecursoChange = (index, e) => {
        const tipo = e.target.value;
        const nuevosLotes = [...lotes];

        nuevosLotes[index].tipoRecurso = tipo;
        const opciones = RECURSOS_POR_TIPO[tipo] || [];
        nuevosLotes[index].descripcion = opciones[0] || '';

        setLotes(nuevosLotes);
    };

    useEffect(() => {
        if (!emergenciaId) {
            setError('No se especificó el parámetro emergenciaId en la URL.');
            return;
        }

        setLoadingEmergencia(true);

        Promise.all([obtenerEmergenciaPorId(emergenciaId), reformulando ? obtenerLotes(emergenciaId) : []])
            .then(([data, lotesEmergencia]) => {
                if (!reformulando && data.estado !== EMERGENCIA_ESTADOS.CREADA) {
                    setError('La emergencia seleccionada no se encuentra pendiente de desglose.');
                    return;
                }
                setLotesReemplazados((lotesEmergencia || []).filter(lote => lotesAReformular.includes(lote.id)));
                setEmergenciaSeleccionada(data);
            })
            .catch((err) => {
                setError(err.message);
            })
            .finally(() => {
                setLoadingEmergencia(false);
            });
    }, [emergenciaId, searchParams]);

    const handleAddLote = () => {
        setLotes([
            ...lotes,
            {
                tipoRecurso: 'Insumos',
                descripcion: RECURSOS_POR_TIPO['Insumos']?.[0] || 'Raciones de comida',
                cantidad: 1
            }
        ]);
    };

    const handleLoteChange = (index, e) => {
        const nuevosLotes = [...lotes];
        nuevosLotes[index][e.target.name] = e.target.value;
        setLotes(nuevosLotes);
    };

    const handleRemoveLote = (index) => {
        if (lotes.length === 1) return;
        const nuevosLotes = lotes.filter((_, i) => i !== index);
        setLotes(nuevosLotes);
    };

    const getBadgeGravedad = (gravedad) => {
        switch (normalizeNivelGravedad(gravedad)) {
            case NIVELES_GRAVEDAD.CRITICO:
                return <span className="badge bg-danger text-uppercase px-3 py-2">Gravedad: {getNivelGravedadLabel(gravedad)}</span>;
            case NIVELES_GRAVEDAD.ALTO:
                return <span className="badge bg-warning text-dark text-uppercase px-3 py-2">Gravedad: {getNivelGravedadLabel(gravedad)}</span>;
            case NIVELES_GRAVEDAD.MEDIO:
                return <span className="badge bg-info text-dark text-uppercase px-3 py-2">Gravedad: {getNivelGravedadLabel(gravedad)}</span>;
            default:
                return <span className="badge bg-secondary text-uppercase px-3 py-2">Gravedad: {getNivelGravedadLabel(gravedad)}</span>;
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!emergenciaSeleccionada || saving) return;

        setSubmitError('');

        // Validamos únicamente que la descripción no esté vacía y la cantidad sea válida
        if (
            lotes.some(
                lote =>
                    !lote.descripcion?.trim() ||
                    !Number.isSafeInteger(Number(lote.cantidad)) ||
                    Number(lote.cantidad) < 1
            )
        ) {
            setSubmitError(
                'Seleccione un recurso específico y una cantidad entera mayor a cero en cada lote.'
            );
            return;
        }

        const payload = {
            emergenciaId: emergenciaSeleccionada.id,
            lotes: lotes.map(lote => ({
                ...lote,
                descripcion: lote.descripcion.trim(),
                cantidad: Number(lote.cantidad)
            }))
        };

        try {
            setSaving(true);
            if (reformulando) {
                await decidirEmergencia(emergenciaSeleccionada.id, {
                    accion: 'reformular',
                    lotes: lotesAReformular,
                    nuevosLotes: payload.lotes
                });
            } else {
                await crearLotes(payload);
            }
            navigate('/dashboard', { state: { mensajeExito: 'Lotes publicados y convocatoria abierta con éxito.' } });
        } catch (err) {
            setSubmitError(err.message);
        } finally {
            setSaving(false);
        }
    };

    if (error) {
        return <div className="panel"><p className="notice notice-error" role="alert">{error}</p><Link className="btn btn-outline-secondary" to="/lotes/nuevo">Elegir otra emergencia</Link></div>;
    }

    if (loadingEmergencia || !emergenciaSeleccionada) {
        return <div className="text-center my-5">Cargando datos de la emergencia...</div>;
    }

    return (
        <div className={styles.page}>
            <div className="row justify-content-center">
                <div className="col-12">
                    <div className="panel">
                        <div className={styles.content}>
                            <h1 className={styles.title}>
                                {reformulando ? 'Reformular lotes y abrir convocatoria' : 'Crear lotes y abrir convocatoria'}
                            </h1>

                            <ValidatedForm key={lotes.length} onSubmit={handleSubmit} aria-busy={saving}>
                                <fieldset disabled={saving}>
                                <div className={styles.summary}>
                                    <div className={styles.row}>
                                        <h5 className="mb-0 fw-bold">
                                            Zona afectada: {emergenciaSeleccionada.zonaAfectada}
                                        </h5>
                                        {getBadgeGravedad(emergenciaSeleccionada.nivelGravedad)}
                                    </div>

                                    <p className="text-muted mb-0">
                                        {emergenciaSeleccionada.descripcionInicial}
                                    </p>

                                    {reformulando && (
                                        <div className="mt-3">
                                            <p className="mb-1 fw-bold">Estos lotes se reemplazan por los que cargues abajo:</p>
                                            <ul className="mb-0">
                                                {lotesReemplazados.map(lote => (
                                                    <li key={lote.id}>{lote.tipoRecurso} · {lote.descripcion} (pedido: {lote.cantidad})</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>

                                <hr className="my-4" />

                                <div className={styles.row}>
                                    <h5 className="mb-0 fw-bold">Lotes de recursos requeridos</h5>
                                    <button
                                        type="button"
                                        className="btn btn-outline-secondary"
                                        onClick={handleAddLote}
                                    >
                                        + Agregar otro lote
                                    </button>
                                </div>

                                {lotes.map((lote, index) => (
                                    <div key={index} className={styles.lote}>
                                        <div className={styles.row}>
                                            <span className="badge bg-secondary">Lote #{index + 1}</span>
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

                                        <div className="row g-3">
                                            <div className="col-md-3">
                                                <label htmlFor={`tipo-${index}`} className="form-label small fw-bold">Tipo de recurso</label>
                                                <select
                                                    className="form-select form-select-sm"
                                                    name="tipoRecurso"
                                                    id={`tipo-${index}`}
                                                    data-validation-key={`tipo-${index}`}
                                                    value={lote.tipoRecurso}
                                                    onChange={(e) => handleTipoRecursoChange(index, e)}
                                                    required
                                                >
                                                    {TIPOS_RECURSOS.map((tipo) => (
                                                        <option key={tipo} value={tipo}>{tipo}</option>
                                                    ))}
                                                </select>
                                                <FieldError name={`tipo-${index}`} />
                                            </div>

                                            <div className="col-md-6">
                                                <label htmlFor={`descripcion-${index}`} className="form-label small fw-bold">Recurso específico</label>
                                                <select
                                                    className="form-select form-select-sm"
                                                    name="descripcion"
                                                    id={`descripcion-${index}`}
                                                    data-validation-key={`descripcion-${index}`}
                                                    value={lote.descripcion}
                                                    onChange={(e) => handleLoteChange(index, e)}
                                                    required
                                                 >
                                                    {(RECURSOS_POR_TIPO[lote.tipoRecurso] || []).map((recurso) => (
                                                        <option key={recurso} value={recurso}>{recurso}</option>
                                                    ))}
                                                 </select>
                                                <FieldError name={`descripcion-${index}`} />
                                            </div>

                                            <div className="col-md-3">
                                                <label htmlFor={`cantidad-${index}`} className="form-label small fw-bold">Cantidad requerida</label>
                                                <input
                                                    type="number"
                                                    className="form-control form-control-sm"
                                                    name="cantidad"
                                                    data-required-message="Ingrese la cantidad requerida."
                                                    id={`cantidad-${index}`}
                                                    data-validation-key={`cantidad-${index}`}
                                                    step="1"
                                                    min="1"
                                                    value={lote.cantidad}
                                                    onChange={(e) => handleLoteChange(index, e)}
                                                    required
                                                />
                                                <FieldError name={`cantidad-${index}`} />
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                <div className="form-actions">
                                    {reformulando
                                        ? <Link className="btn btn-outline-secondary" to="/emergencias/evaluar">Volver a la evaluación</Link>
                                        : <Link className="btn btn-outline-secondary" to="/lotes/nuevo">Elegir otra emergencia</Link>}
                                    <button
                                        type="submit"
                                        className="btn btn-primary"
                                    >
                                        {saving ? 'Publicando…' : 'Publicar lotes y abrir convocatoria'}
                                    </button>
                                </div>
                                </fieldset>
                                {submitError && <p className="notice notice-error mt-3" role="alert">{submitError}</p>}
                            </ValidatedForm>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};