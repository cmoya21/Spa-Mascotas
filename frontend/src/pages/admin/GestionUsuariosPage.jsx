import { useEffect, useMemo, useState } from "react";

import {
  apiActualizarEstadoUsuario,
  apiCambiarPasswordUsuario,
  apiCrearUsuario,
  apiListRoles,
  apiListUsuarios,
} from "../../api/usuariosApi";
import Alert from "../../components/shared/Alert";
import Button from "../../components/shared/Button";
import InputField from "../../components/shared/InputField";

const EMPTY_FORM = {
  email: "",
  password: "",
  rol_nombre: "Cliente",
  nombre: "",
};

export default function GestionUsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [passwordTarget, setPasswordTarget] = useState(null);
  const [newPassword, setNewPassword] = useState("");

  const rolOptions = useMemo(() => {
    if (roles.length) return roles;
    return ["Admin", "Recepcion", "Groomer", "Cliente"].map((nombre, index) => ({ id: index + 1, nombre }));
  }, [roles]);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [usuariosData, rolesData] = await Promise.all([
        apiListUsuarios(),
        apiListRoles().catch(() => ({ roles: [] })),
      ]);
      setUsuarios(usuariosData.usuarios || []);
      setRoles(rolesData.roles || []);
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudieron cargar los usuarios.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarDatos();
  }, []);

  const handleCrear = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await apiCrearUsuario(form);
      setSuccess("Usuario creado correctamente.");
      setForm(EMPTY_FORM);
      setShowModal(false);
      await cargarDatos();
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo crear el usuario.");
    }
  };

  const handleToggle = async (usuario) => {
    setError("");
    try {
      await apiActualizarEstadoUsuario(usuario.id, !usuario.estado_activo);
      await cargarDatos();
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo actualizar el estado.");
    }
  };

  const handleCambiarPassword = async () => {
    if (!passwordTarget) return;
    setError("");
    try {
      await apiCambiarPasswordUsuario(passwordTarget.id, newPassword);
      setSuccess("Contraseña actualizada correctamente.");
      setPasswordTarget(null);
      setNewPassword("");
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo cambiar la contraseña.");
    }
  };

  return (
    <div className="page-shell">
      <section className="agenda-card agenda-wide">
        <div className="modal-header" style={{ marginBottom: 16 }}>
          <div>
            <p className="calendar-kicker">Administración</p>
            <h2 style={{ margin: 0 }}>Gestión de usuarios</h2>
          </div>
          <Button onClick={() => setShowModal(true)}>+ Nuevo usuario</Button>
        </div>

        {success ? <Alert message={success} success /> : null}
        {error ? <Alert message={error} /> : null}

        <div style={{ overflowX: "auto" }}>
          <table className="table-view" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>Email</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Último acceso</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => (
                <tr key={usuario.id}>
                  <td>{usuario.email}</td>
                  <td>{usuario.rol || "-"}</td>
                  <td>{usuario.estado_activo ? "Activo" : "Inactivo"}</td>
                  <td>{usuario.ultimo_acceso ? new Date(usuario.ultimo_acceso).toLocaleString() : "-"}</td>
                  <td style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button type="button" className="link-button" onClick={() => handleToggle(usuario)}>
                      {usuario.estado_activo ? "Desactivar" : "Activar"}
                    </button>
                    <button type="button" className="link-button" onClick={() => setPasswordTarget(usuario)}>
                      Cambiar contraseña
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {loading ? <div className="admin-empty" style={{ marginTop: 16 }}>Cargando usuarios...</div> : null}
      </section>

      {showModal ? (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ width: "min(640px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Nuevo usuario</p>
                <h3 style={{ margin: 0 }}>Crear cuenta</h3>
              </div>
              <button type="button" className="ghost-button" onClick={() => setShowModal(false)}>
                Cerrar
              </button>
            </div>
            <form onSubmit={handleCrear} className="form-group">
              <InputField label="Email" type="email" value={form.email} onChange={(value) => setForm((prev) => ({ ...prev, email: value }))} required />
              <InputField label="Contraseña" type="password" value={form.password} onChange={(value) => setForm((prev) => ({ ...prev, password: value }))} required />
              <div className="input-field">
                <label>Rol</label>
                <div className="input-wrapper">
                  <select className="select-field" value={form.rol_nombre} onChange={(e) => setForm((prev) => ({ ...prev, rol_nombre: e.target.value }))}>
                    {rolOptions.map((rol) => (
                      <option key={rol.id} value={rol.nombre}>
                        {rol.nombre}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <InputField label="Nombre" value={form.nombre} onChange={(value) => setForm((prev) => ({ ...prev, nombre: value }))} />
              <Button>Crear usuario</Button>
            </form>
          </div>
        </div>
      ) : null}

      {passwordTarget ? (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ width: "min(520px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Cambiar contraseña</p>
                <h3 style={{ margin: 0 }}>{passwordTarget.email}</h3>
              </div>
              <button type="button" className="ghost-button" onClick={() => setPasswordTarget(null)}>
                Cerrar
              </button>
            </div>
            <div className="form-group">
              <InputField label="Nueva contraseña" type="password" value={newPassword} onChange={setNewPassword} required />
              <Button onClick={handleCambiarPassword}>Guardar contraseña</Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}