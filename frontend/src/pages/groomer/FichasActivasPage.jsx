import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthContext } from '../../context/AuthContext.jsx'

export default function FichasActivasPage() {
  const navigate = useNavigate()
  const [fichas, setFichas] = useState([])
  const [cargando, setCargando] = useState(false)
  const { apiCall } = useAuthContext()

  const fetchFichas = async () => {
    setCargando(true)
    try {
      const token = localStorage.getItem('access_token') ||
                    localStorage.getItem('token')
      const res = await fetch('/api/groomers/me/agenda?fecha=' +
        new Date().toISOString().slice(0, 10), {
        headers: { Authorization: `Bearer ${token}` }
      })
      const data = await res.json()
      const lista = Array.isArray(data) ? data : data?.citas || []
      setFichas(lista.filter(c =>
        c.ficha?.estado !== 'cerrada' &&
        c.estado !== 'cancelada' &&
        c.estado !== 'completada'
      ))
    } catch (e) {
      console.error(e)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { fetchFichas() }, [])

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
        📋 Fichas activas
      </h2>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 24, fontSize: 14 }}>
        Citas de hoy con fichas en curso o por iniciar.
      </p>

      {cargando && (
        <p style={{ color: 'var(--color-text-tertiary)' }}>Cargando fichas...</p>
      )}

      {!cargando && fichas.length === 0 && (
        <div style={{
          padding: 32, textAlign: 'center',
          background: 'var(--color-background-secondary)',
          borderRadius: 'var(--border-radius-md)',
          color: 'var(--color-text-secondary)'
        }}>
          ✅ No tienes fichas activas por ahora.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {fichas.map(cita => (
          <div key={cita.id} style={{
            border: '0.5px solid var(--color-border-tertiary)',
            borderRadius: 'var(--border-radius-md)',
            padding: '14px 16px',
            background: 'var(--color-background-primary)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12
          }}>
            <div>
              <p style={{ fontWeight: 500, margin: 0, fontSize: 14 }}>
                🐾 {cita.mascota?.nombre || 'Mascota'} ·{' '}
                {cita.mascota?.raza || 'Sin raza'}
              </p>
              <p style={{
                fontSize: 13, color: 'var(--color-text-secondary)',
                margin: '2px 0 0'
              }}>
                ✂️ {cita.servicio?.nombre} · {cita.hora_inicio} — {cita.hora_fin}
              </p>
              {cita.ficha?.estado === 'en_curso' && (
                <span style={{
                  display: 'inline-block', marginTop: 6,
                  fontSize: 12, fontWeight: 500,
                  background: '#FAEEDA', color: '#633806',
                  padding: '2px 8px', borderRadius: 20
                }}>
                  🔄 En curso
                </span>
              )}
              {cita.ficha?.estado === 'sin_iniciar' && (
                <span style={{
                  display: 'inline-block', marginTop: 6,
                  fontSize: 12, color: 'var(--color-text-tertiary)',
                  padding: '2px 8px', borderRadius: 20,
                  border: '0.5px solid var(--color-border-tertiary)'
                }}>
                  Por iniciar
                </span>
              )}
            </div>
            <button
              onClick={() => {
                if (cita.ficha?.id) {
                  navigate(`/fichas/${cita.ficha.id}`)
                } else {
                  navigate(`/fichas/nueva?cita_id=${cita.id}`)
                }
              }}
              style={{
                background: '#1D9E75', color: 'white',
                border: 'none', borderRadius: 'var(--border-radius-md)',
                padding: '8px 16px', cursor: 'pointer',
                fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap'
              }}
            >
              {cita.ficha?.id ? 'Ver ficha →' : 'Iniciar ficha'}
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 20, textAlign: 'center' }}>
        <button
          onClick={() => navigate('/groomers/agenda')}
          style={{
            background: 'none', border: '0.5px solid var(--color-border-secondary)',
            borderRadius: 'var(--border-radius-md)', padding: '8px 20px',
            cursor: 'pointer', fontSize: 13,
            color: 'var(--color-text-secondary)'
          }}
        >
          ← Volver a mi agenda
        </button>
      </div>
    </div>
  )
}
