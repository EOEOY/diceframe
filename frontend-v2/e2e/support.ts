import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

export const accessToken = () => {
  const dataDir = process.env.DICEFRAME_E2E_DATA_DIR || '../data'
  return readFileSync(resolve(dataDir, 'access_token.txt'), 'utf8').trim()
}
