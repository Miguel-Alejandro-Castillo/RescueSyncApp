import { useEffect, useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { exportarIndicadores, obtenerIndicadores } from '../../services/indicadoresService';
import styles from './Indicadores.module.css';

const COLORES = ['#5aa9e6', '#7fc8a9', '#f2c14e', '#e07a5f', '#b392d6', '#8fa3b8'];
const ESTADOS = {
  creada: 'Creada',
  publicada: 'Publicada',
  convocatoria_cerrada: 'Convocatoria cerrada',
  en_adjudicacion: 'En adjudicación',
  adjudicada: 'Adjudicada',
  monitoreo_finalizado: 'Finalizada',
};
const DATASETS = [
  { valor: 'completo', etiqueta: 'Reporte completo (solo JSON)' },
  { valor: 'resumen', etiqueta: 'Resumen de indicadores' },
  { valor: 'proyectos', etiqueta: 'Estado de proyectos' },
  { valor: 'suministros_por_tipo', etiqueta: 'Suministros por tipo' },
  { valor: 'suministros_por_mes', etiqueta: 'Suministros por mes' },
  { valor: 'etapas', etiqueta: 'Tiempos por etapa (Bonita)' },
];
const TOOLTIP_STYLE = {
  contentStyle: { background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--ink)' },
  itemStyle: { color: 'var(--ink)' },
  labelStyle: { color: 'var(--ink)' },
  cursor: { fill: 'rgba(255,255,255,0.06)' },
};
const EJE = { stroke: 'var(--muted)', fontSize: 12 };

const numero = (valor, sufijo = '') => (valor === null || valor === undefined ? '—' : `${valor.toLocaleString('es-AR')}${sufijo}`);

function Kpi({ titulo, valor, detalle }) {
  return (
    <div className={styles.kpi}>
      <span className={styles.kpiTitulo}>{titulo}</span>
      <strong className={styles.kpiValor}>{valor}</strong>
      {detalle && <span className={styles.kpiDetalle}>{detalle}</span>}
    </div>
  );
}

function Grafico({ titulo, descripcion, vacio, children }) {
  return (
    <section className={styles.grafico} aria-label={titulo}>
      <h2>{titulo}</h2>
      {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
      {vacio ? <p className={styles.vacio}>Sin datos para el período elegido.</p> : (
        <div className={styles.lienzo}>
          <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export default function Indicadores() {
  const [mes, setMes] = useState('');
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [estadoFiltro, setEstadoFiltro] = useState('');
  const [dataset, setDataset] = useState('completo');
  const [exportando, setExportando] = useState(false);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError('');
    obtenerIndicadores(mes)
      .then(resultado => vigente && setDatos(resultado))
      .catch(err => vigente && setError(err.message))
      .finally(() => vigente && setCargando(false));
    return () => { vigente = false; };
  }, [mes]);

  const handleExportar = async formato => {
    setExportando(true);
    setError('');
    try {
      await exportarIndicadores({ formato, dataset, mes });
    } catch (err) {
      setError(err.message);
    } finally {
      setExportando(false);
    }
  };

  const consorcios = datos?.consorcios;
  const datosConsorcio = consorcios ? [
    { nombre: 'Consorcios', valor: consorcios.ofertas_consorcio },
    { nombre: 'Individuales', valor: consorcios.ofertas_individuales },
  ] : [];
  const estados = useMemo(() => (datos?.proyectos_por_estado ?? []).map(item => ({
    ...item, nombre: ESTADOS[item.estado] ?? item.estado,
  })), [datos]);
  const proyectos = useMemo(() => (datos?.proyectos ?? []).filter(p => !estadoFiltro || p.estado === estadoFiltro), [datos, estadoFiltro]);
  const bonita = datos?.bonita;
  const kpis = datos?.kpis;

  return (
    <div className={styles.page}>
      <div className="page-heading">
        <h1>Indicadores de gestión</h1>
        <p>Métricas del sistema y tiempos del proceso en Bonita para evaluar y hacer seguimiento de las emergencias.</p>
      </div>

      <div className={styles.barra}>
        <div>
          <label htmlFor="filtro-mes" className="form-label">Período</label>
          <div className={styles.fila}>
            <input id="filtro-mes" type="month" className="form-control" value={mes} onChange={e => setMes(e.target.value)} />
            <button type="button" className="btn btn-outline-secondary" onClick={() => setMes('')} disabled={!mes}>Todo el período</button>
          </div>
        </div>
        <div>
          <label htmlFor="export-dataset" className="form-label">Exportar datos</label>
          <div className={styles.fila}>
            <select id="export-dataset" className="form-select" value={dataset} onChange={e => setDataset(e.target.value)}>
              {DATASETS.map(d => <option key={d.valor} value={d.valor}>{d.etiqueta}</option>)}
            </select>
            <button type="button" className="btn btn-primary" onClick={() => handleExportar('csv')} disabled={exportando || !datos || dataset === 'completo'}>CSV</button>
            <button type="button" className="btn btn-primary" onClick={() => handleExportar('json')} disabled={exportando || !datos}>JSON</button>
          </div>
        </div>
      </div>

      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {cargando && <p role="status">Cargando indicadores...</p>}

      {datos && !cargando && <>
        <div className={styles.kpis}>
          <Kpi titulo="Suministros movilizados" valor={numero(kpis.suministros_movilizados)} detalle="unidades adjudicadas" />
          <Kpi titulo="Resolución por consorcios" valor={numero(kpis.porcentaje_resolucion_consorcios, '%')}
            detalle={`${consorcios.ofertas_consorcio} de ${consorcios.ofertas_total} ofertas adjudicadas`} />
          <Kpi titulo="Proyectos finalizados" valor={`${kpis.emergencias_finalizadas} / ${kpis.emergencias_total}`}
            detalle={`${numero(kpis.porcentaje_finalizadas, '%')} de las emergencias`} />
          <Kpi titulo="Duración promedio de un caso" valor={numero(kpis.duracion_promedio_caso_horas, ' h')}
            detalle={kpis.casos_en_curso_bonita === null ? 'Bonita no disponible' : `${kpis.casos_en_curso_bonita} casos en curso`} />
        </div>

        <div className={styles.graficos}>
          <Grafico titulo="Suministros por tipo de recurso" vacio={datos.suministros_por_tipo.length === 0}>
            <BarChart data={datos.suministros_por_tipo}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="tipo" {...EJE} />
              <YAxis {...EJE} allowDecimals={false} />
              <Tooltip {...TOOLTIP_STYLE} formatter={valor => [valor, 'Unidades']} />
              <Bar dataKey="cantidad" name="Unidades" radius={[4, 4, 0, 0]}>
                {datos.suministros_por_tipo.map((item, i) => <Cell key={item.tipo} fill={COLORES[i % COLORES.length]} />)}
              </Bar>
            </BarChart>
          </Grafico>

          <Grafico titulo="Suministros movilizados por mes" descripcion="Últimos 6 meses, independiente del período elegido.">
            <BarChart data={datos.suministros_por_mes}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="mes" {...EJE} />
              <YAxis {...EJE} allowDecimals={false} />
              <Tooltip {...TOOLTIP_STYLE} formatter={valor => [valor, 'Unidades']} />
              <Bar dataKey="cantidad" name="Unidades" fill={COLORES[0]} radius={[4, 4, 0, 0]} />
            </BarChart>
          </Grafico>

          <Grafico titulo="Resolución por consorcios" descripcion="Ofertas adjudicadas según tengan una o varias ONGs." vacio={consorcios.ofertas_total === 0}>
            <PieChart>
              <Pie data={datosConsorcio} dataKey="valor" nameKey="nombre" innerRadius="45%" outerRadius="75%" paddingAngle={2} stroke="var(--surface)">
                {datosConsorcio.map((item, i) => <Cell key={item.nombre} fill={COLORES[i]} />)}
              </Pie>
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend />
            </PieChart>
          </Grafico>

          <Grafico titulo="Estado de los proyectos" descripcion="Hacé clic en una barra para filtrar la tabla de proyectos.">
            <BarChart data={estados} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis type="number" {...EJE} allowDecimals={false} />
              <YAxis type="category" dataKey="nombre" width={140} {...EJE} />
              <Tooltip {...TOOLTIP_STYLE} formatter={valor => [valor, 'Emergencias']} />
              <Bar dataKey="cantidad" name="Emergencias" radius={[0, 4, 4, 0]} cursor="pointer"
                onClick={item => setEstadoFiltro(actual => (actual === item.estado ? '' : item.estado))}>
                {estados.map((item, i) => (
                  <Cell key={item.estado} fill={COLORES[i % COLORES.length]} fillOpacity={!estadoFiltro || estadoFiltro === item.estado ? 1 : 0.35} />
                ))}
              </Bar>
            </BarChart>
          </Grafico>

          <section className={`${styles.grafico} ${styles.ancho}`} aria-label="Tiempos promedio por etapa">
            <h2>Tiempo promedio por etapa de la emergencia</h2>
            <p className={styles.descripcion}>
              Datos de la API de Bonita: horas entre la finalización de una tarea y la de la anterior del mismo caso.
            </p>
            {!bonita.disponible && <div className="notice notice-error" role="alert"><p>{bonita.error}</p></div>}
            {bonita.disponible && bonita.etapas.length === 0 && <p className={styles.vacio}>Todavía no hay tareas completadas en el período.</p>}
            {bonita.etapas.length > 0 && (
              <div className={styles.lienzoAlto}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={bonita.etapas} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                    <XAxis type="number" {...EJE} unit=" h" />
                    <YAxis type="category" dataKey="etapa" width={260} {...EJE} />
                    <Tooltip {...TOOLTIP_STYLE} formatter={(valor, _n, { payload }) => [
                      `${valor} h (mín. ${payload.minimo_horas} · máx. ${payload.maximo_horas} · ${payload.muestras} muestras)`, 'Promedio',
                    ]} />
                    <Bar dataKey="promedio_horas" name="Promedio (h)" fill={COLORES[3]} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>
        </div>

        <section className={styles.tabla} aria-label="Detalle de proyectos">
          <div className={styles.tablaTitulo}>
            <h2>Detalle de proyectos{estadoFiltro && ` — ${ESTADOS[estadoFiltro] ?? estadoFiltro}`}</h2>
            {estadoFiltro && <button type="button" className="btn btn-outline-secondary" onClick={() => setEstadoFiltro('')}>Quitar filtro</button>}
          </div>
          {proyectos.length === 0 ? <p className={styles.vacio}>No hay proyectos para mostrar.</p> : (
            <div className={styles.scroll}>
              <table>
                <thead>
                  <tr>
                    <th>#</th><th>Zona</th><th>Gravedad</th><th>Estado</th><th>Creada</th>
                    <th>Lotes adjudicados</th><th>Cobertura</th><th>ONGs finalizadas</th>
                  </tr>
                </thead>
                <tbody>
                  {proyectos.map(p => (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>{p.zona}</td>
                      <td>{p.gravedad}</td>
                      <td>{ESTADOS[p.estado] ?? p.estado}</td>
                      <td>{new Date(p.fecha_creacion).toLocaleDateString('es-AR')}</td>
                      <td>{p.lotes_adjudicados} / {p.lotes_total}</td>
                      <td>{p.cobertura_pct}%</td>
                      <td>{p.ongs_finalizadas} / {p.ongs_adjudicadas}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </>}
    </div>
  );
}
