import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { crearEmergencia } from '../../services/emergenciaService';

// Importación de estilos específicos para el componente AltaEmergencia
import styles from './AltaEmergencia.module.css';

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
        const response = await crearEmergencia(formData)
        if (response) {
            //  enviar a la página de dashboard o limpiar el formulario
            setFormData(initialFormData);
            // Aquí se podría mostrar un mensaje de éxito al usuario antes de redirigir
            alert("Emergencia creada con éxito");
            // Redirigir a la página de dashboard mediante react-router-dom
            // Aquí se podría usar el hook useNavigate de react-router-dom para redirigir
            const navigate = useNavigate();
            navigate("/dashboard");
        } else {
            // Manejar el caso en que la creación de la emergencia falle
            console.error("Error al crear la emergencia");
            alert("Error al crear la emergencia");
        }



    };

    return (
        <div className={styles.page}>
            <div className="container">
                <div className="row justify-content-center">
                    <div className="col-12 col-md-8 col-lg-6">
                        <div className={`card ${styles.card}`}>
                            <div className={`card-body ${styles.cardBody}`}>
                                <h1 className={`h3 text-center ${styles.title}`}>Alta Emergencia</h1>
                                <form className={styles.form} onSubmit={handleSubmit}>
                                    <div className={styles.field}>
                                        <label className={styles.label}>Zona Afectada:</label>
                                        <input
                                            type="text"
                                            className={styles.input}
                                            name="zonaAfectada"
                                            value={formData.zonaAfectada}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                    <div className={styles.field}>
                                        <label className={styles.label}>Nivel de gravedad:</label>
                                        <select
                                            className={styles.select}
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
                                    <div className={styles.field}>
                                        <label className={styles.label}>Descripcion Inicial:</label>
                                        <textarea
                                            className={styles.textarea}
                                            name="descripcionInicial"
                                            value={formData.descripcionInicial}
                                            onChange={handleChange}
                                            rows="4"
                                            required
                                        />
                                    </div>
                                    <div className="d-grid">
                                        <button type="submit" className={styles.submit}>Guardar</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AltaEmergencia;
