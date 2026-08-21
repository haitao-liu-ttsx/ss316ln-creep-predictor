export interface Params { T: number; P: number; t: number; Rm: number; Ro: number; w: number }

export interface PredictResult {
  valid: boolean
  status: string
  violations?: string[]
  reason?: string
  field?: number[]
  max_ceeq?: number
  mean_ceeq?: number
  p95_ceeq?: number
  hotspot_element?: number
  hotspot_xyz?: number[]
  hotspot_value?: number
  pod_coefficients?: number[]
  physics_status?: string
  stress_scale?: number
}

export async function predict(p: Params): Promise<PredictResult> {
  const r = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p),
  })
  return r.json()
}

/* ---- STEP21-D: V1.3 7-field multiphysics prediction ---- */
export interface V13FieldSummary { min: number; max: number; mean: number; p95: number }
export interface V13Result {
  status: string
  errors?: string[]
  model_version?: string
  schema_version?: string
  inputs?: { T: number; P: number; t: number; Rm: number; Ro: number; w: number; P_Ro_w: number }
  domain_status?: 'SAFE' | 'WARNING' | 'OUT_OF_DOMAIN'
  domain_reasons?: string[]
  centroids?: number[][]
  fields?: Record<string, number[]>
  summary?: Record<string, V13FieldSummary>
  global_ranges?: Record<string, [number, number]>
}
export const V13_FIELDS = ['Srr', 'Stt', 'Szz', 'Srt', 'Srz', 'Stz', 'CEEQ', 'von_mises'] as const
export const V13_FIELD_ZH: Record<string, string> = {
  Srr: '径向应力 Srr', Stt: '环向应力 Sθθ', Szz: '轴向应力 Szz',
  Srt: '面内剪应力 Srθ', Srz: '剪应力 Srz', Stz: '剪应力 Sθz',
  CEEQ: '等效蠕变应变 CEEQ', von_mises: 'von Mises 等效应力',
}
export const V13_UNITS: Record<string, string> = {
  Srr: 'MPa', Stt: 'MPa', Szz: 'MPa', Srt: 'MPa', Srz: 'MPa', Stz: 'MPa',
  CEEQ: '无量纲', von_mises: 'MPa',
}

export async function predictV13(p: Params): Promise<V13Result> {
  const r = await fetch('/api/predict_v13', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p),
  })
  return r.json()
}

export const DEMO_CASES: { name: string; params: Params }[] = [
  { name: 'Demo Case 1（基准几何 300h）', params: { T: 600, P: 20, t: 300, Rm: 100, Ro: 20, w: 4 } },
  { name: 'Demo Case 2（Rm150 3000h）', params: { T: 650, P: 20, t: 3000, Rm: 150, Ro: 20, w: 4 } },
  { name: 'Demo Case 3（非基准几何高应力 3000h）', params: { T: 650, P: 25, t: 3000, Rm: 120, Ro: 25, w: 3 } },
  { name: 'Demo Case 4（OOD: T=700°C）', params: { T: 700, P: 10, t: 100, Rm: 100, Ro: 20, w: 4 } },
]

export const DOMAIN = {
  T: [550, 650], P: [2.5, 30], t: [1, 3000], Rm: [80, 150], Ro: [15, 25], w: [2, 5],
}
export const STRESS_MAX = 250
