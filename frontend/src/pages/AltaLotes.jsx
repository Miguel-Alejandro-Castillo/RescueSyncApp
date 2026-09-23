import React, { useState } from 'react';
import { crearLotes } from '../services/lotesService';

// Simulación de emergencias registradas pendientes de desglose y publicación
const MOCK_EMERGENCIAS_PENDIENTES = [
    {
        id: "EMG-101",
        zonaAfectada: "Municipio de Quilmes - Sector Este",
        nivelGravedad: "critico",
        descripcionInicial: "Inundación por desborde de arroyo. Se requieren refugios y atención médica urgente.",
        tiempoVentana: "2 horas"
    },
    {
        id: "EMG-102",
        zonaAfectada: "Zona Norte - Tigre",
        nivelGravedad: "alto",
        descripcionInicial: "Temporal de viento y lluvia con caída de postes de luz y anegamientos.",
        tiempoVentana: "6 horas"
    },
    {
        id: "EMG-103",
        zonaAfectada: "La Plata - Casco Urbano",
        nivelGravedad: "medio",
        descripcionInicial: "Anegamiento puntual de avenidas principales sin evacuados de gravedad.",
        tiempoVentana: "12 horas"
    }
];

const AltaLotes = () => {
    const [emergenciaSeleccionada, setEmergenciaSeleccionada] = useState(null);
    const [lotes, setLotes] = useState([
        { tipoRecurso: 'Insumos', descripcion: '', cantidad: 1 }
    ]);

    const handleEmergenciaChange = (e) => {
        const id = e.target.value;
        const encontrada = MOCK_EMERGENCIAS_PENDIENTES.find(item => item.id === id);
        setEmergenciaSeleccionada(encontrada || null);
    };

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
        switch (gravedad) {
            case 'critico': return <span className="badge bg-danger">Gravedad: CRÍTICA</span>;
            case 'alto': return <span className="badge bg-warning text-dark">Gravedad: ALTA</span>;
            case 'medio': return <span className="badge bg-info text-dark">Gravedad: MEDIA</span>;
            default: return <span className="badge bg-secondary">Gravedad: BAJA</span>;
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!emergenciaSeleccionada) return;

        const payload = {
            emergenciaId: emergenciaSeleccionada.id,
            duracionConvocatoria: emergenciaSeleccionada.tiempoVentana,
            lotes
        };

        console.log("Payload enviado (Apertura de convocatoria):", payload);
        await crearLotes(payload);
    };

    return (
        <div className="container mt-4 mb-5">
            <div className="row justify-content-center">
                <div className="col-12 col-lg-10">
                    <div className="card shadow-sm border-0 rounded-4">
                        <div className="card-body p-4">
                            <h1 className="h3 mb-2 text-center">Desglose de Lotes y Apertura de Convocatoria</h1>
                            <p className="text-muted text-center mb-4 small">
                                Centro Coordinador de Emergencias - Publicación de necesidades para la red de ONGs
                            </p>

                            <form onSubmit={handleSubmit}>
                                {/* SELECCIÓN DE EMERGENCIA */}
                                <div className="mb-4">
                                    <label className="form-label fw-bold">Seleccionar Emergencia Registrada Pendiente:</label>
                                    <select
                                        className="form-select"
                                        value={emergenciaSeleccionada ? emergenciaSeleccionada.id : ''}
                                        onChange={handleEmergenciaChange}
                                        required
                                    >
                                        <option value="">-- Seleccione una emergencia para desglosar --</option>
                                        {MOCK_EMERGENCIAS_PENDIENTES.map(emg => (
                                            <option key={emg.id} value={emg.id}>
                                                [{emg.id}] {emg.zonaAfectada} ({emg.nivelGravedad.toUpperCase()})
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* TARJETA DE RESUMEN Y VENTANA DE TIEMPO DE LA EMERGENCIA */}
                                {emergenciaSeleccionada && (
                                    <div className="card border-primary bg-light mb-4 p-3 rounded-3">
                                        <div className="d-flex justify-content-between align-items-center mb-2">
                                            <h6 className="mb-0 fw-bold text-primary">
                                                📍 {emergenciaSeleccionada.zonaAfectada}
                                            </h6>
                                            {getBadgeGravedad(emergenciaSeleccionada.nivelGravedad)}
                                        </div>

                                        <p className="small text-muted mb-2">
                                            {emergenciaSeleccionada.descripcionInicial}
                                        </p>

                                        <div className="alert alert-warning py-2 mb-0 d-flex align-items-center gap-2 small">
                                            <span>⏳</span>
                                            <div>
                                                <strong>Ventana de Convocatoria:</strong> Según el nivel de gravedad, las ONGs tendrán 
                                                <strong className="text-dark"> {emergenciaSeleccionada.tiempoVentana}</strong> para enviar sus ofertas de ayuda una vez publicada.
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <hr className="my-4" />

                                {/* DESGLOSE DE LOTES */}
                                <div className="d-flex justify-content-between align-items-center mb-3">
                                    <h5 className="mb-0">Lotes de Recursos Requeridos</h5>
                                    <button
                                        type="button"
                                        className="btn btn-outline-success btn-sm"
                                        onClick={handleAddLote}
                                        disabled={!emergenciaSeleccionada}
                                    >
                                        ＋ Agregar otro lote
                                    </button>
                                </div>

                                {lotes.map((lote, index) => (
                                    <div key={index} className="card bg-light border-0 mb-3 p-3 rounded-3">
                                        <div className="d-flex justify-content-between align-items-center mb-2">
                                            <span className="badge bg-secondary">Lote #{index + 1}</span>
                                            {lotes.length > 1 && (
                                                <button
                                                    type="button"
                                                    className="btn btn-outline-danger btn-sm border-0"
                                                    onClick={() => handleRemoveLote(index)}
                                                >
                                                    🗑️ Eliminar
                                                </button>
                                            )}
                                        </div>

                                        <div className="row g-2">
                                            <div className="col-md-3">
                                                <label className="form-label small">Tipo de Recurso:</label>
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
                                                <label className="form-label small">Descripción Específica:</label>
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
                                                <label className="form-label small">Cantidad Requerida:</label>
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

                                {/* BOTÓN DE ACCIÓN CLEAR */}
                                <div className="d-grid mt-4">
                                    <button
                                        type="submit"
                                        className="btn btn-primary btn-lg"
                                        disabled={!emergenciaSeleccionada}
                                    >
                                        🚀 Publicar Lotes y Abrir Convocatoria
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
