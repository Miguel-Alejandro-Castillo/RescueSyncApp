import React, { useState } from 'react';
import { crearLotes } from '../services/lotesService';

const AltaLotes = () => {
    const [emergenciaId, setEmergenciaId] = useState('');
    const [lotes, setLotes] = useState([
        { tipoRecurso: 'Insumos', descripcion: '', cantidad: 1 }
    ]);

    const handleEmergenciaChange = (e) => {
        setEmergenciaId(e.target.value);
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = {
            emergenciaId,
            lotes
        };
        console.log("Payload enviado:", payload);
        await crearLotes(payload);
    };

    return (
        <div className="container mt-4 mb-5">
            <div className="row justify-content-center">
                <div className="col-12 col-lg-10">
                    <div className="card shadow-sm border-0 rounded-4">
                        <div className="card-body p-4">
                            <h1 className="h3 mb-4 text-center">Publicación de Lotes de Necesidades</h1>
                            
                            <form onSubmit={handleSubmit}>
                                <div className="mb-4">
                                    <label className="form-label fw-bold">Seleccionar Emergencia Activa:</label>
                                    <select
                                        className="form-select"
                                        value={emergenciaId}
                                        onChange={handleEmergenciaChange}
                                        required
                                    >
                                        <option value="">-- Seleccione una emergencia --</option>
                                        <option value="EMG-101">Inundación Zona Norte (Gravedad: Alta)</option>
                                        <option value="EMG-102">Temporal Quilmes (Gravedad: Crítica)</option>
                                    </select>
                                </div>

                                <hr className="my-4" />

                                <div className="d-flex justify-content-between align-items-center mb-3">
                                    <h5 className="mb-0">Lotes de Recursos Requeridos</h5>
                                    <button 
                                        type="button" 
                                        className="btn btn-outline-success btn-sm"
                                        onClick={handleAddLote}
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
                                                <label className="form-label small">Descripción:</label>
                                                <input
                                                    type="text"
                                                    className="form-control form-control-sm"
                                                    name="descripcion"
                                                    placeholder="Ej. Agua potable 2L / Médicos de guardia"
                                                    value={lote.descripcion}
                                                    onChange={(e) => handleLoteChange(index, e)}
                                                    required
                                                />
                                            </div>

                                            <div className="col-md-3">
                                                <label className="form-label small">Cantidad:</label>
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
                                    <button type="submit" className="btn btn-primary btn-lg">
                                        Publicar Lotes de Necesidades
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
