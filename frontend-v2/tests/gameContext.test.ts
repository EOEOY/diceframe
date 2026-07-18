import { describe, expect, it, beforeEach, vi } from 'vitest'
import {
  clearCurrentGame,
  readCurrentGame,
  rememberCurrentGame,
  gameFromQuery,
} from '../src/stores/gameContext'

describe('gameContext', () => {
  beforeEach(() => {
    const store = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => { store.set(key, String(value)) },
      removeItem: (key: string) => { store.delete(key) },
      clear: () => { store.clear() },
    })
    localStorage.clear()
  })

  it('reads legacy current game and writes both keys', () => {
    localStorage.setItem('trpg_current_game', 'legacy-game')
    expect(readCurrentGame()).toBe('legacy-game')

    rememberCurrentGame('new-game', '暗潮堡')
    expect(localStorage.getItem('currentGame')).toBe('new-game')
    expect(localStorage.getItem('trpg_current_game')).toBe('new-game')
    expect(localStorage.getItem('trpg_current_game_name')).toBe('暗潮堡')
  })

  it('only clears the active game when the key matches', () => {
    rememberCurrentGame('game-a')
    clearCurrentGame('game-b')
    expect(readCurrentGame()).toBe('game-a')

    clearCurrentGame('game-a')
    expect(readCurrentGame()).toBe('')
  })

  it('normalizes router query values', () => {
    expect(gameFromQuery({ game: ['first', 'second'] })).toBe('first')
    expect(gameFromQuery({ game: 'single' })).toBe('single')
  })
})
