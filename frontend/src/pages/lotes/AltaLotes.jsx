import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {  obtenerEmergenciaPorId,crearLotes } from '../../services/lotesService';

const AltaLotes = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const emergenciaId = searchParams.get('emergenciaId');

    const [emergenciaSeleccionada, setEmergenciaSeleccionada] = useState(null);
    const [loadingEmergencia, setLoadingEmergencia] = useState(false);
    const [error, setError] = useState('');

    const [lotes, setLotes] = useState([
        { tipoRecurso: 'Insumos', descripcion: '', cantidad: 1 }
    ]);

    useEffect(() => {
        if (!emergenciaId) {
            setError('No se especificó el parámetro emergenciaId en la URL.');
            return;
        }

        setLoadingEmergencia(true);

        obtenerEmergenciaPorId(emergenciaId)
            .then((data) => {
                if (data.estado !== 'creada') {
                    setError('La emergencia seleccionada no se encuentra pendiente de desglose.');
                    return;
                }
                setEmergenciaSeleccionada(data);
            })
            .catch((err) => {
                setError(err.message);
            })
            .finally(() => {
                setLoadingEmergencia(false);
            });
    }, [emergenciaId]);

    const handleLoteChange = (index, e) => {
        const { name, value } = e.target;
        const nuevosLotes = [...lotes];
        nuevosLotes[index][name] = value;
        setLotes(nuevosLotes);
    };

    const handleAddLote = () => {
        setLotes([
            ...lotes,
            { tipoRecurso: 'Insumos', descripcion: '', cantidad: 1 }
        ]);
    };

    const handleRemoveLote = (index) => {
        if (lotes.length === 1) return;
        const nuevosLotes = lotes.filter((_, i) => i !== index);
        setLotes(nuevosLotes);
    };

    const getBadgeGravedad = (gravedad) => {
        switch (gravedad?.toLowerCase()) {
            case 'critico':
                return <span className="badge bg-danger text-uppercase px-3 py-2">Gravedad: Crítica</span>;
            case 'alto':
                return <span className="badge bg-warning text-dark text-uppercase px-3 py-2">Gravedad: Alta</span>;
            case 'medio':
                return <span className="badge bg-info text-dark text-uppercase px-3 py-2">Gravedad: Media</span>;
            default:
                return <span className="badge bg-secondary text-uppercase px-3 py-2">Gravedad: Baja</span>;
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!emergenciaSeleccionada) return;

        const payload = {
            emergenciaId: emergenciaSeleccionada.id,
            lotes
        };

        try {
            await crearLotes(payload);
            alert('Lotes publicados y convocatoria abierta con éxito.');
            navigate('/dashboard');
        } catch (err) {
            alert(`Error al publicar lotes: ${err.message}`);
        }
    };

    if (error) {
        return <div className="alert alert-danger m-4 text-center">{error}</div>;
    }

    if (loadingEmergencia || !emergenciaSeleccionada) {
        return <div className="text-center my-5">Cargando datos de la emergencia...</div>;
    }

    return (
        <div className="container mt-4 mb-5">
            <div className="row justify-content-center">
                <div className="col-12 col-lg-10">
                    <div className="card shadow-sm border-0 rounded-4">
                        <div className="card-body p-4">
                            <h1 className="h3 mb-4 text-center text-primary fw-bold">
                                Desglose de Lotes y Apertura de Convocatoria
                            </h1>

                            <form onSubmit={handleSubmit}>
                                {/* RESUMEN DE LA EMERGENCIA */}
                                <div className="card border-primary-subtle bg-light mb-4 p-3 rounded-3 shadow-sm">
                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                        <h5 className="mb-0 fw-bold text-dark">
                                            Zona Afectada: {emergenciaSeleccionada.zonaAfectada}
                                        </h5>
                                        {getBadgeGravedad(emergenciaSeleccionada.nivelGravedad)}
                                    </div>

                                    <p className="text-secondary mb-0">
                                        {emergenciaSeleccionada.descripcionInicial}
                                    </p>
                                </div>

                                <hr className="my-4" />

                                {/* DESGLOSE DE LOTES */}
                                <div className="d-flex justify-content-between align-items-center mb-3">
                                    <h5 className="mb-0 fw-bold text-dark">Lotes de Recursos Requeridos</h5>
                                    <button
                                        type="button"
                                        className="btn btn-success btn-sm font-weight-bold"
                                        onClick={handleAddLote}
                                    >
                                        + Agregar otro lote
                                    </button>
                                </div>

                                {lotes.map((lote, index) => (
                                    <div key={index} className="card bg-white border mb-3 p-3 rounded-3 shadow-sm">
                                        <div className="d-flex justify-content-between align-items-center mb-2">
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
                                                <label className="form-label small fw-bold">Tipo de Recurso:</label>
                                                <select
                                                    className="form-select form-select-sm"
                                                    name="tipoRecurso"
                                                    value={lote.tipoRecurso}
                                                    onChange={(e) => handleLoteChange(index, e)}
                                                    required
                                                >
                                                    <option value="Insumos">Insumos / Alimentos</option>
                                                    <option value="Personal">Personal / Voluntarios</option>
                                                    <option value="Maquinaria">Maquinaria / Vehículos</option>
                                                    <option value="Refugio">Refugio / Abrigo</option>
                                                </select>
                                            </div>

                                            <div className="col-md-6">
                                                <label className="form-label small fw-bold">Descripción Específica:</label>
                                                <input
                                                    type="text"
                                                    className="form-control form-control-sm"
                                                    name="descripcion"
                                                    placeholder="Ej. Agua potable 2L / Paramédicos de emergencia"
                                                    value={lote.descripcion}
                                                    onChange={(e) => handleLoteChange(index, e)}
                                                    required
                                                />
                                            </div>

                                            <div className="col-md-3">
                                                <label className="form-label small fw-bold">Cantidad Requerida:</label>
                                                <input
                                                    type="number"
                                                    className="form-control form-control-sm"
                                                    name="cantidad"
                                                    min="1"
                                                    value={lote.cantidad}
                                                    onChange={(e) => handleLoteChange(index, e)}
                                                    required
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                <div className="d-grid mt-4">
                                    <button
                                        type="submit"
                                        className="btn btn-primary btn-lg font-weight-bold"
                                    >
                                        Publicar Lotes y Abrir Convocatoria
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AltaLotes;
