import { describe, expect, it } from 'vitest'
import { calcAutoHp, suggestedAttributes } from '../src/utils/ruleSchema'

describe('ruleSchema helpers', () => {
  it('calculates CoC 7e HP from percentile CON and SIZ', () => {
    expect(calcAutoHp({ con: 50, siz: 60 }, { mechanics: 'coc7e_core' })).toBe(11)
  })

  it('fills suggested attributes up to the rule total without exceeding max', () => {
    const attrs = [
      { key: 'str', name: '力量', min: 3, max: 18 },
      { key: 'dex', name: '敏捷', min: 3, max: 18 },
      { key: 'con', name: '体质', min: 3, max: 18 },
      { key: 'int', name: '智力', min: 3, max: 18 },
      { key: 'wis', name: '感知', min: 3, max: 18 },
      { key: 'cha', name: '魅力', min: 3, max: 18 },
    ]

    const suggested = suggestedAttributes(attrs, 60)
    expect(Object.values(suggested).reduce((sum, value) => sum + value, 0)).toBe(60)
    expect(Object.values(suggested).every(value => value >= 3 && value <= 18)).toBe(true)
  })
})
