let chartEtapas;

function actualizarTotal(etapa, costoMaterial) {
  const manoObra = parseFloat(document.getElementById(`mano_obra_${etapa}`).value || 0);
  const costoTotal = costoMaterial + manoObra;
  document.getElementById(`total_${etapa}`).textContent = `S/ ${costoTotal.toFixed(2)}`;

  actualizarTotalGeneral();
  actualizarGrafico();
}

function actualizarTotalGeneral() {
  const etapas = ['acero', 'cimentacion', 'muro', 'columna', 'viga', 'techo'];
  let totalGeneral = 0;
  etapas.forEach(etapa => {
    const valor = parseFloat(document.getElementById(`total_${etapa}`).textContent.replace('S/ ', '')) || 0;
    totalGeneral += valor;
  });
  document.getElementById('total_general').textContent = `S/ ${totalGeneral.toFixed(2)}`;
}

function obtenerCosto(etapa) {
  return parseFloat(document.getElementById(`total_${etapa}`).textContent.replace('S/ ', '')) || 0;
}

function actualizarGrafico() {
  const etapas = ['acero', 'cimentacion', 'muro', 'columna', 'viga', 'techo'];
  const nombres = [
    'Acero Columna',
    'Cimentación',
    'Muro',
    'Columna',
    'Viga y Techo (Armado)',
    'Viga y Techo (Vaciado)'
  ];
  const costos = etapas.map(etapa => obtenerCosto(etapa));

  if (chartEtapas) {
    chartEtapas.data.datasets[0].data = costos;
    chartEtapas.update();
  }
}

window.addEventListener('load', () => {
  const ctx = document.getElementById('graficoEtapas').getContext('2d');
  const etapas = ['acero', 'cimentacion', 'muro', 'columna', 'viga', 'techo'];
  const nombres = [
    'Acero Columna',
    'Cimentación',
    'Muro',
    'Columna',
    'Viga y Techo (Armado)',
    'Viga y Techo (Vaciado)'
  ];
  const costos = etapas.map(etapa => obtenerCosto(etapa));

  chartEtapas = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: nombres,
      datasets: [{
        label: 'Costo por Etapa (S/)',
        data: costos,
        backgroundColor: '#007bff',
        borderRadius: 5
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `S/ ${ctx.raw.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 45,
            autoSkip: false
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: value => `S/ ${value}`
          }
        }
      }      
    }
  });
});
