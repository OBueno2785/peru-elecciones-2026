/**
 * Normaliza un nombre de departamento para hacer match entre
 * el GeoJSON del Perú y los datos de ONPE.
 */
export function normName(s) {
  if (!s) return '';
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')  // quitar tildes
    .toUpperCase()
    .trim()
    // Equivalencias de nombres
    .replace(/^SAN MARTIN$/, 'SAN MARTIN')
    .replace(/^LA LIBERTAD$/, 'LA LIBERTAD')
    .replace(/^MADRE DE DIOS$/, 'MADRE DE DIOS');
}

/**
 * Formatea un número con separadores de miles.
 */
export function fmtNum(n) {
  if (n == null) return '–';
  return Number(n).toLocaleString('es-PE');
}

/**
 * Formatea un porcentaje.
 */
export function fmtPct(n) {
  if (n == null) return '–';
  return Number(n).toFixed(2) + '%';
}

/**
 * Genera el color de una barra de progreso/porcentaje.
 */
export function progressColor(pct) {
  if (pct >= 60) return '#22c55e';
  if (pct >= 30) return '#f59e0b';
  return '#ef4444';
}

/**
 * Lista de tipos de elección disponibles.
 */
export const TIPOS_ELECCION = [
  {
    id: 'presidencial',
    label: 'Presidencial',
    endpoint: '/api/presidencial',
    desc: 'Elección nacional — el mapa muestra el avance de conteo de actas por departamento',
  },
  {
    id: 'senado-regional',
    label: 'Senado Regional',
    endpoint: '/api/senado-regional',
    desc: 'Senado por distrito electoral múltiple — resultados por departamento',
  },
  {
    id: 'diputados',
    label: 'Diputados',
    endpoint: '/api/diputados',
    desc: 'Cámara de Diputados — resultados por departamento',
  },
  {
    id: 'carrera',
    label: '🏁 Carrera 2° Puesto',
    endpoint: null,
    desc: 'Evolución en tiempo real de la carrera por el segundo puesto presidencial',
  },
  {
    id: 'jee',
    label: '⚖️ Flujo JEE',
    endpoint: null,
    desc: 'Flujo de actas: contabilizadas por ONPE, enviadas al JEE y pendientes de certificación',
  },
  {
    id: 'composicion-jee',
    label: '📊 Composición JEE',
    endpoint: null,
    desc: 'Composición real del voto en actas certificadas por el JEE, por departamento',
  },
  {
    id: 'comparacion',
    label: '⚖️ Comparación de escenarios',
    endpoint: null,
    desc: 'Comparación de resultados: sin JEE · con JEE · solo JEE · actas pendientes',
  },
  {
    id: 'actas-dashboard',
    label: '📋 Actas EDA',
    endpoint: null,
    desc: 'Análisis exploratorio de actas descargadas: consistencia, participación y distribución geográfica',
  },
  {
    id: 'consulta-actas',
    label: '🔍 Consulta Actas',
    endpoint: null,
    desc: 'Consulta individual de actas: imagen del PDF escaneado vs. datos digitados en el sistema ONPE',
  },
];
