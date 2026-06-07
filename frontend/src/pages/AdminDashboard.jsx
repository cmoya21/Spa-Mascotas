import { useEffect, useMemo, useState } from "react";

import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";
import InventoryAlertBadge from "../components/shared/InventoryAlertBadge";
import CampanaNotificaciones from "../components/shared/CampanaNotificaciones.jsx";
import { useAuthContext } from "../context/AuthContext.jsx";
import {
  apiActualizarEstadoUsuario,
  apiCrearEmpleado,
  apiListClientes,
  apiListUsuarios
} from "../api/adminApi";
import { apiListCitas } from "../api/agendaApi.js";
import { apiGetAlertasInventarioActivos } from "../api/alertasApi.js";

const initialForm = {
  nombres: "",
  apellidos: "",
  email: "",
  password: "",
  telefono: "",
  rol: "Recepcion",
  especialidad: "",
  turno: ""
};

export default function AdminDashboard() {
  const { usuario } = useAuthContext();
  const [form, setForm] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [usuarios, setUsuarios] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingClientes, setLoadingClientes] = useState(false);
  const [view, setView] = useState("crear");
  const [solicitudesPendientes, setSolicitudesPendientes] = useState(0);
  const [alertasCriticas, setAlertasCriticas] = useState(0);

  const totalActivos = useMemo(
    () => usuarios.filter((item) => item.estado_activo).length,
    [usuarios]
  );

  const updateField = (key) => (value) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const resolveErrorMessage = (err, fallback) => {
    const message = err?.response?.data?.message;
    const details = err?.response?.data?.details;
    if (details) {
      const firstKey = Object.keys(details)[0];
      if (firstKey && details[firstKey]?.length) {
        return `${details[firstKey][0]}`;
      }
    }
    return message || fallback;
  };

  const cargarUsuarios = async () => {
    setLoadingList(true);
    try {
      const data = await apiListUsuarios();
      setUsuarios(data.usuarios || []);
    } catch (err) {
      setError(resolveErrorMessage(err, "No se pudo cargar la lista de usuarios."));
    } finally {
      setLoadingList(false);
    }
  };

  const cargarClientes = async () => {
    setLoadingClientes(true);
    try {
      const data = await apiListClientes();
      setClientes(data.clientes || []);
    } catch (err) {
      setError(resolveErrorMessage(err, "No se pudo cargar la lista de clientes."));
    } finally {
      setLoadingClientes(false);
    }
  };

  useEffect(() => {
    cargarUsuarios();
    cargarClientes();
  }, []);

  useEffect(() => {
    const cargarSolicitudes = async () => {
      try {
        const data = await apiListCitas({ estado: "agendada" });
        setSolicitudesPendientes((data.citas || []).length);
      } catch (err) {
        setSolicitudesPendientes(0);
      }
    };

    cargarSolicitudes();
    const intervalId = setInterval(cargarSolicitudes, 60000);
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    const cargarAlertas = async () => {
      try {
        const data = await apiGetAlertasInventarioActivos();
        setAlertasCriticas(data.total_criticos ?? data.total ?? 0);
      } catch (err) {
        setAlertasCriticas(0);
      }
    };

    cargarAlertas();
    const intervalId = setInterval(cargarAlertas, 5 * 60 * 1000);
    return () => clearInterval(intervalId);
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const payload = {
        nombres: form.nombres,
        apellidos: form.apellidos,
        email: form.email,
        password: form.password,
        telefono: form.telefono || null,
        rol: form.rol,
        especialidad: form.rol === "Groomer" ? form.especialidad : null,
        turno: form.rol === "Groomer" ? form.turno : null
      };
      await apiCrearEmpleado(payload);
      setSuccess("Empleado creado correctamente.");
      setForm({ ...initialForm, rol: form.rol });
      await cargarUsuarios();
    } catch (err) {
      setError(resolveErrorMessage(err, "No se pudo crear el empleado. Verifica los datos."));
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEstado = async (usuarioId, activoActual) => {
    setError("");
    try {
      await apiActualizarEstadoUsuario(usuarioId, !activoActual);
      await cargarUsuarios();
    } catch (err) {
      setError(resolveErrorMessage(err, "No se pudo actualizar el estado del usuario."));
    }
  };

  return (
    <div className="admin-layout">
      <div className="admin-shell">
        <div className="admin-hero">
          <div>
            <h2>Panel de Administración</h2>
            <p>Gestión rápida de personal y clientes del Pet Spa.</p>
          </div>
          <div className="admin-metrics">
            <div>
              <span>Usuarios activos</span>
              <strong>{totalActivos}</strong>
            </div>
            <div>
              <span>Total clientes</span>
              <strong>{clientes.length}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <CampanaNotificaciones />
            </div>
          </div>
        </div>

        <div className="admin-layout-grid">
          <section className="admin-content">
            {view === "crear" && (
              <div className="admin-card">
                <h3>Crear cuenta de empleado</h3>
                <p>Solo Recepción y Groomers.</p>
                <form onSubmit={handleSubmit} className="form-group">
          <InputField
            label="Nombres"
            icon="👤"
            value={form.nombres}
            onChange={updateField("nombres")}
            placeholder="Ej. Ana Maria"
          />
          <InputField
            label="Apellidos"
            icon="👤"
            value={form.apellidos}
            onChange={updateField("apellidos")}
            placeholder="Ej. Lopez"
          />
          <InputField
            label="Correo"
            icon="✉"
            value={form.email}
            onChange={updateField("email")}
            placeholder="personal@petspa.com"
          />
          <InputField
            label="Telefono"
            icon="📞"
            value={form.telefono}
            onChange={updateField("telefono")}
            placeholder="70000000"
          />
          <div className="input-field">
            <label>Rol</label>
            <div className="input-wrapper">
              <span className="icon-left">🛡</span>
              <select
                className="select-field"
                value={form.rol}
                onChange={(e) => updateField("rol")(e.target.value)}
              >
                <option value="Recepcion">Recepcion</option>
                <option value="Groomer">Groomer</option>
              </select>
            </div>
          </div>
          {form.rol === "Groomer" && (
            <>
              <InputField
                label="Especialidad"
                icon="✨"
                value={form.especialidad}
                onChange={updateField("especialidad")}
                placeholder="Corte, bano, spa"
              />
              <InputField
                label="Turno"
                icon="⏰"
                value={form.turno}
                onChange={updateField("turno")}
                placeholder="Manana / Tarde"
              />
            </>
          )}
          <InputField
            label="Contrasena"
            type={showPassword ? "text" : "password"}
            icon="🔒"
            value={form.password}
            onChange={updateField("password")}
            placeholder="Minimo 8 caracteres"
            rightElement={showPassword ? "Ocultar" : "Mostrar"}
            error={""}
          />
          <div style={{ textAlign: "right" }}>
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="link-text"
              style={{ background: "none", border: "none" }}
            >
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          <Button loading={loading}>Crear cuenta</Button>
          <Alert message={error || success} success={!!success} />
                </form>
              </div>
            )}

            {view === "empleados" && (
              <div className="admin-card">
                <div className="admin-card-header">
                  <div>
                    <h3>Cuentas del sistema</h3>
                    <p>Activa o desactiva usuarios.</p>
                  </div>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={cargarUsuarios}
                    disabled={loadingList}
                  >
                    {loadingList ? "Actualizando..." : "Refrescar"}
                  </button>
                </div>
                <div className="admin-table">
                  <div className="admin-row admin-head">
                    <span>Usuario</span>
                    <span>Rol</span>
                    <span>Estado</span>
                    <span>Accion</span>
                  </div>
                  {usuarios.map((item) => (
                    <div className="admin-row" key={item.id}>
                      <span>{item.email}</span>
                      <span className="pill">{item.rol || "-"}</span>
                      <span className={item.estado_activo ? "status ok" : "status off"}>
                        {item.estado_activo ? "Activo" : "Inactivo"}
                      </span>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => handleToggleEstado(item.id, item.estado_activo)}
                      >
                        {item.estado_activo ? "Dar de baja" : "Activar"}
                      </button>
                    </div>
                  ))}
                  {!usuarios.length && !loadingList && (
                    <div className="admin-empty">No hay usuarios registrados.</div>
                  )}
                </div>
              </div>
            )}

            {view === "clientes" && (
              <div className="admin-card">
                <div className="admin-card-header">
                  <div>
                    <h3>Clientes registrados</h3>
                    <p>Listado general de clientes.</p>
                  </div>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={cargarClientes}
                    disabled={loadingClientes}
                  >
                    {loadingClientes ? "Actualizando..." : "Refrescar"}
                  </button>
                </div>
                <div className="admin-table">
                  <div className="admin-row admin-head">
                    <span>Cliente</span>
                    <span>Telefono</span>
                    <span>Direccion</span>
                    <span>Estado</span>
                  </div>
                  {clientes.map((item) => (
                    <div className="admin-row" key={item.id}>
                      <span>{item.nombre} {item.apellido || ""}</span>
                      <span>{item.telefono || "-"}</span>
                      <span>{item.direccion || "-"}</span>
                      <span className={item.estado_activo ? "status ok" : "status off"}>
                        {item.estado_activo ? "Activo" : "Inactivo"}
                      </span>
                    </div>
                  ))}
                  {!clientes.length && !loadingClientes && (
                    <div className="admin-empty">No hay clientes registrados.</div>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
