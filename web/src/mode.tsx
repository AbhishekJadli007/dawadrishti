import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { View } from './api'

// Public view shows the published record only. Buyer view adds the graded response, model scores and alternatives.
const Ctx = createContext<{ view: View; setView: (v: View) => void }>({ view: 'public', setView: () => {} })

export function ViewProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<View>(() => {
    try { return (localStorage.getItem('dd-view') as View) || 'public' } catch { return 'public' }
  })
  useEffect(() => { try { localStorage.setItem('dd-view', view) } catch { /* private mode */ } }, [view])
  return <Ctx.Provider value={{ view, setView }}>{children}</Ctx.Provider>
}

export const useView = () => useContext(Ctx)
