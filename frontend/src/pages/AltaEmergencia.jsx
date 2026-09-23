import React, { useState } from 'react';
import { crearEmergencia } from '../services/emergenciaService';

const initialFormData = {
    zonaAfectada: "",
    nivelGravedad: "medio",
    descripcionInicial: ""
};
const AltaEmergencia = () => {
    const [formData, setFormData] = useState(initialFormData);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({
            ...formData,
            [name]: value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        await crearEmergencia(formData);
    };

    return (
        <div className="container mt-4">
            <div className="row justify-content-center">
                <div className="col-12 col-md-8 col-lg-6">
                    <div className="card shadow-sm border-0 rounded-4">
                        <div className="card-body p-4">
                            <h1 className="h3 mb-4 text-center">Alta Emergencia</h1>
                            <form onSubmit={handleSubmit}>
                                <div className="mb-3">
                                    <label className="form-label">Zona Afectada:</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        name="zonaAfectada"
                                        value={formData.zonaAfectada}
                                        onChange={handleChange}
                                        required
                                    />
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">Nivel de gravedad:</label>
                                    <select
                                        className="form-select"
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
                                </div>
                                <div className="mb-4">
                                    <label className="form-label">Descripcion Inicial:</label>
                                    <textarea
                                        className="form-control"
                                        name="descripcionInicial"
                                        value={formData.descripcionInicial}
                                        onChange={handleChange}
                                        rows="4"
                                        required
                                    />
                                </div>
                                <div className="d-grid">
                                    <button type="submit" className="btn btn-primary">Guardar</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AltaEmergencia;
