// chart 2
var ctx2 = document.getElementById("chart-line").getContext("2d");
var ctx = document.getElementById("chart-bars").getContext("2d");

var gradientStroke1 = ctx2.createLinearGradient(0, 230, 0, 50);
gradientStroke1.addColorStop(1, "rgba(203,12,159,0.2)");
gradientStroke1.addColorStop(0.2, "rgba(72,72,176,0.0)");
gradientStroke1.addColorStop(0, "rgba(203,12,159,0)");

var gradientStroke2 = ctx2.createLinearGradient(0, 230, 0, 50);
gradientStroke2.addColorStop(1, "rgba(20,23,39,0.2)");
gradientStroke2.addColorStop(0.2, "rgba(72,72,176,0.0)");
gradientStroke2.addColorStop(0, "rgba(20,23,39,0)");

var gradientStroke3 = ctx2.createLinearGradient(0, 230, 0, 50);
gradientStroke3.addColorStop(1, "rgba(0,150,136,0.2)");
gradientStroke3.addColorStop(0.2, "rgba(72,72,176,0.0)");
gradientStroke3.addColorStop(0, "rgba(0,150,136,0)");

// Function to fetch data from API
async function fetchChartData() {
  try {
    let response = await fetch("/api/monthly-contributions/");
    let data = await response.json();
    updateChart(data.months, data.contributions, data.withdrawals, data.credits);
    updateChart2(data.months, data.repayments);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

// Function to update chart with real data
function updateChart(months, contributions, withdrawals='', credits='') {
  new Chart(ctx2, {
    type: "line",
    data: {
      labels: months,
      datasets: [
        {
          label: "Credits",
          tension: 0.4,
          borderWidth: 3,
          borderColor: "#cb0c9f",
          backgroundColor: gradientStroke1,
          fill: true,
          data: credits,
          maxBarThickness: 6,
        },
        {
          label: "Withdrawals",
          tension: 0.4,
          borderWidth: 3,
          borderColor: "#3A416F",
          backgroundColor: gradientStroke2,
          fill: true,
          data: withdrawals,
          maxBarThickness: 6,
        },
        {
          label: "Contributions",
          tension: 0.4,
          borderWidth: 3,
          borderColor: "#009688",
          backgroundColor: gradientStroke3,
          fill: true,
          data: contributions,
          maxBarThickness: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
      },
      scales: {
        y: {
          grid: { borderDash: [5, 5] },
          ticks: { padding: 10 },
        },
        x: {
          grid: { display: false },
          ticks: { padding: 10 },
        },
      },
    },
  });
}

function updateChart2(months, repayments) {

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: months,
      datasets: [
        {
          label: "Repayments",
          tension: 0.4,
          borderWidth: 0,
          borderRadius: 4,
          borderSkipped: false,
          backgroundColor: "#fff",
          data: repayments,
          maxBarThickness: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      interaction: {
        intersect: false,
        mode: "index",
      },
      scales: {
        y: {
          grid: {
            drawBorder: false,
            display: false,
            drawOnChartArea: false,
            drawTicks: false,
          },
          ticks: {
            suggestedMin: 0,
            suggestedMax: 600,
            beginAtZero: true,
            padding: 15,
            font: {
              size: 14,
              family: "Open Sans",
              style: "normal",
              lineHeight: 2,
            },
            color: "#fff",
          },
        },
        x: {
          grid: {
            drawBorder: false,
            display: false,
            drawOnChartArea: false,
            drawTicks: false,
          },
          ticks: {
            display: false,
          },
        },
      },
    },
  });
}
// Fetch data on page load
fetchChartData();
