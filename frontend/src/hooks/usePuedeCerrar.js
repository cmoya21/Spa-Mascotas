import { useEffect, useState } from "react";
import { apiGetEstadoCierre } from "../api/groomerApi.js";

export default function usePuedeCerrar(fichaId) {
  const [state, setState] = useState({ loading: true, puede_cerrar: false, razones_bloqueo: [], checklist: {}, fotos: {} });

  useEffect(() => {
    let active = true;
    if (!fichaId) {
      setState({ loading: false, puede_cerrar: false, razones_bloqueo: [], checklist: {}, fotos: {} });
      return () => (active = false);
    }
    setState((s) => ({ ...s, loading: true }));
    apiGetEstadoCierre(fichaId)
      .then((data) => {
        if (!active) return;
        setState({ loading: false, ...data });
      })
      .catch(() => {
        if (!active) return;
        setState({ loading: false, puede_cerrar: false, razones_bloqueo: [], checklist: {}, fotos: {} });
      });
    return () => {
      active = false;
    };
  }, [fichaId]);

  return state;
}
