import { useEffect, useState } from "react";

import { apiGetBeneficiosFrecuente } from "../../api/clienteApi.js";

const nivelEmoji = {
  Gold: "🥇",
  Silver: "🥈",
  Bronze: "🥉",
  Nuevo: "✨",
};

export default function BeneficiosFrecuente() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGetBeneficiosFrecuente()
      .then(setData)
      .catch(() => setError("No se pudieron cargar tus beneficios."));
  }, []);

  if (error) {
    return <div className="client-benefits client-benefits-error">{error}</div>;
  }

  if (!data) {
    return <div className="client-benefits">Cargando beneficios...</div>;
  }

  return (
    <section className="client-benefits">
      <div className="client-benefits-head">
        <strong>{nivelEmoji[data.nivel] || "✨"} {data.nivel}</strong>
        <span>{data.total_visitas} visitas completadas</span>
      </div>
      {data.descuento_disponible > 0 ? (
        <div className="client-benefits-banner">
          🎉 Tienes {data.descuento_disponible}% de descuento en tu próxima visita
        </div>
      ) : (
        <div className="client-benefits-banner muted">{data.mensaje}</div>
      )}
    </section>
  );
}
