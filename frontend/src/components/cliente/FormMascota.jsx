import { useEffect, useState, useMemo } from "react";

import Button from "../shared/Button";
import InputField from "../shared/InputField";

const EMPTY_FORM = {
  nombre: "",
  especie: "",
  raza: "",
  tamano: "",
  fecha_nacimiento: "",
  peso_kg: "",
  temperamento: "",
  alergias_conocidas: "",
  restricciones_medicas: "",
  observaciones: "",
};

const TAMANO_SUGGESTIONS = {
  pequeno: 5,
  mediano: 15,
  grande: 30,
  gigante: 50,
};

const toInputValue = (value) => (value === null || value === undefined ? "" : String(value));

export default function FormMascota({ initialValue, onSubmit, onCancel, busy = false }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [fotoFile, setFotoFile] = useState(null);
  const [carnetFile, setCarnetFile] = useState(null);
  const [fotoPreview, setFotoPreview] = useState(null);
  const [carnetPreview, setCarnetPreview] = useState(null);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (!initialValue) {
      setForm(EMPTY_FORM);
      setFotoPreview(null);
      setCarnetPreview(null);
      setFotoFile(null);
      setCarnetFile(null);
      setErrors({});
      return;
    }
    setForm({
      nombre: toInputValue(initialValue.nombre),
      especie: toInputValue(initialValue.especie),
      raza: toInputValue(initialValue.raza),
      tamano: toInputValue(initialValue.tamano),
      fecha_nacimiento: toInputValue(initialValue.fecha_nacimiento),
      peso_kg: toInputValue(initialValue.peso_kg),
      temperamento: toInputValue(initialValue.temperamento),
      alergias_conocidas: toInputValue(initialValue.alergias_conocidas),
      restricciones_medicas: toInputValue(initialValue.restricciones_medicas),
      observaciones: toInputValue(initialValue.observaciones),
    });
    setFotoPreview(initialValue.foto_url || null);
    setCarnetPreview(initialValue.carnet_vacunas_url || null);
  }, [initialValue]);

  useEffect(() => {
    if (!fotoFile) return;
    const url = URL.createObjectURL(fotoFile);
    setFotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [fotoFile]);

  useEffect(() => {
    if (!carnetFile) return;
    const url = URL.createObjectURL(carnetFile);
    setCarnetPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [carnetFile]);

  const handleChange = (key, value) => setForm((cur) => ({ ...cur, [key]: value }));

  const edad = useMemo(() => {
    if (!form.fecha_nacimiento) return null;
    try {
      const dob = new Date(form.fecha_nacimiento);
      const diff = Date.now() - dob.getTime();
      const years = Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25));
      return years;
    } catch (e) {
      return null;
    }
  }, [form.fecha_nacimiento]);

  const handleFile = (field, file) => {
    // simple client validations
    if (!file) return;
    const maxSize = field === 'foto' ? 5 * 1024 * 1024 : 10 * 1024 * 1024;
    if (file.size > maxSize) {
      setErrors((e) => ({ ...e, [field]: ['Archivo demasiado grande'] }));
      return;
    }
    if (field === 'foto') setFotoFile(file);
    if (field === 'carnet') setCarnetFile(file);
    setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const buildPayload = () => {
    const payload = {};
    Object.entries(form).forEach(([k, v]) => {
      const val = typeof v === 'string' ? v.trim() : v;
      if (val !== '' && val !== null && val !== undefined) payload[k] = val;
    });
    if (form.peso_kg) payload.peso_kg = Number(form.peso_kg);
    return payload;
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    setErrors({});
    const payload = buildPayload();
    if (!payload.nombre || !payload.especie) {
      setErrors({ _form: ['Nombre y especie son obligatorios'] });
      return;
    }

    // prepare FormData if there are files
    let toSend = payload;
    if (fotoFile || carnetFile) {
      const formData = new FormData();
      Object.entries(payload).forEach(([k, v]) => formData.append(k, v));
      if (fotoFile) formData.append('foto', fotoFile);
      if (carnetFile) formData.append('carnet_vacunas', carnetFile);
      toSend = formData;
    }

    await onSubmit?.(toSend).catch((err) => {
      // API returns { errores: { field: ['msg'] } }
      if (err?.errores) setErrors(err.errores);
      else setErrors({ _form: [err?.message || 'Error desconocido'] });
    });
  };

  return (
    <form onSubmit={handleSubmit} className="cliente-form" style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        <InputField label="Nombre" value={form.nombre} onChange={(v) => handleChange('nombre', v)} error={errors.nombre?.[0] || (errors._form && !form.nombre ? errors._form[0] : '')} />
        <InputField label="Especie" value={form.especie} onChange={(v) => handleChange('especie', v)} error={errors.especie?.[0] || (errors._form && !form.especie ? errors._form[0] : '')} />
        <InputField label="Raza" value={form.raza} onChange={(v) => handleChange('raza', v)} />
        <div className="input-field">
          <label>Tamaño</label>
          <div className="input-wrapper">
            <select value={form.tamano} onChange={(e) => handleChange('tamano', e.target.value)}>
              <option value="">Seleccione...</option>
              <option value="pequeno">Pequeño</option>
              <option value="mediano">Mediano</option>
              <option value="grande">Grande</option>
              <option value="gigante">Gigante</option>
            </select>
          </div>
          {form.tamano && (
            <small>Peso sugerido: {TAMANO_SUGGESTIONS[form.tamano] ?? '-'} kg <button type="button" onClick={() => handleChange('peso_kg', TAMANO_SUGGESTIONS[form.tamano] ?? '')} style={{ marginLeft: 8 }}>Autocompletar</button></small>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        <InputField label="Fecha de nacimiento" type="date" value={form.fecha_nacimiento} onChange={(v) => handleChange('fecha_nacimiento', v)} />
        <div className="input-field">
          <label>Peso (kg)</label>
          <div className="input-wrapper">
            <input type="number" value={form.peso_kg} onChange={(e) => handleChange('peso_kg', e.target.value)} />
          </div>
        </div>
        <div className="input-field">
          <label>Temperamento</label>
          <div className="input-wrapper">
            <select value={form.temperamento} onChange={(e) => handleChange('temperamento', e.target.value)}>
              <option value="">Seleccione...</option>
              <option value="tranquilo">Tranquilo</option>
              <option value="ansioso">Ansioso</option>
              <option value="agresivo">Agresivo</option>
            </select>
          </div>
          {form.temperamento === 'agresivo' ? <small className="warning">Marca: agresivo — informar al personal al llegar.</small> : null}
        </div>

        <div className="input-field">
          <label>Foto</label>
          <div className="input-wrapper">
            <input type="file" accept="image/*" onChange={(e) => handleFile('foto', e.target.files?.[0])} />
            {errors.foto ? <div className="field-error">{errors.foto[0]}</div> : null}
            {fotoPreview ? (
              <div style={{ marginTop: 8 }}>
                <img src={fotoPreview} alt="preview" style={{ maxWidth: 160, maxHeight: 120, objectFit: 'cover' }} />
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
        <div className="input-field">
          <label>Carnet de vacunas (PDF o imagen)</label>
          <div className="input-wrapper">
            <input type="file" accept="application/pdf,image/*" onChange={(e) => handleFile('carnet', e.target.files?.[0])} />
            {errors.carnet_vacunas || errors.carnet ? <div className="field-error">{(errors.carnet_vacunas || errors.carnet)[0]}</div> : null}
            {carnetPreview ? (
              <div style={{ marginTop: 8 }}>
                <a href={carnetPreview} target="_blank" rel="noreferrer">Ver carnet</a>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        <InputField label="Alergias conocidas" value={form.alergias_conocidas} onChange={(v) => handleChange('alergias_conocidas', v)} />
        <InputField label="Restricciones médicas" value={form.restricciones_medicas} onChange={(v) => handleChange('restricciones_medicas', v)} />
      </div>

      <div className="input-field">
        <label>Observaciones</label>
        <div className="input-wrapper">
          <textarea value={form.observaciones} onChange={(e) => handleChange('observaciones', e.target.value)} rows={4} style={{ width: '100%', resize: 'vertical', border: 'none', background: 'transparent', outline: 'none' }} />
        </div>
      </div>

      {edad !== null ? <div>Edad aproximada: {edad} años</div> : null}
      {errors._form ? <div className="alert alert-error">{errors._form[0]}</div> : null}

      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        {onCancel ? (
          <button type="button" className="ghost-button" onClick={onCancel}>Cancelar</button>
        ) : null}
        <Button type="submit" disabled={busy}>{busy ? 'Guardando...' : initialValue?.id ? 'Actualizar mascota' : 'Registrar mascota'}</Button>
      </div>
    </form>
  );
}
