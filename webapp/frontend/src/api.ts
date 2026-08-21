/* V1.3 7-field multiphysics prediction API (V1.2 removed) */
export interface Params { T: number; P: number; t: number; Rm: number; Ro: number; w: number }

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
