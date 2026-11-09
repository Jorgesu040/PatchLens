import { useEffect, useState } from 'react'

/**
 * Ejecuta `fetcher(signal)` al montar o cuando cambian `deps`.
 * Devuelve { data, error, loading }.
 */
export default function useFetch(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    const controller = new AbortController()
    setState({ data: null, error: null, loading: true })

    fetcher(controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (!controller.signal.aborted) setState({ data: null, error, loading: false })
      })

    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
