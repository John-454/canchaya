import { describe, expect, it } from 'vitest'

import { fechaCorta, hhmm, lunesDe, nombreDia, sumarDias } from '../lib/format'

describe('utilidades de formato', () => {
  it('recorta la hora a HH:MM', () => {
    expect(hhmm('08:00:00')).toBe('08:00')
    expect(hhmm('21:30')).toBe('21:30')
  })

  it('nombra los días 1..7', () => {
    expect(nombreDia(1)).toBe('Lunes')
    expect(nombreDia(7)).toBe('Domingo')
  })

  it('calcula el lunes de la semana (ISO)', () => {
    expect(lunesDe('2026-12-02')).toBe('2026-11-30') // miércoles -> lunes
    expect(lunesDe('2026-11-30')).toBe('2026-11-30') // lunes -> sí mismo
    expect(lunesDe('2026-12-06')).toBe('2026-11-30') // domingo -> lunes anterior
  })

  it('suma y resta días cruzando meses', () => {
    expect(sumarDias('2026-12-31', 1)).toBe('2027-01-01')
    expect(sumarDias('2026-03-01', -1)).toBe('2026-02-28')
  })

  it('formatea fecha corta en es-CO', () => {
    expect(fechaCorta('2026-12-01')).toMatch(/dic/i)
  })
})
