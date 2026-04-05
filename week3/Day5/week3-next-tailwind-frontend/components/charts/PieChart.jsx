"use client";
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

export default function PieChart() {
  const data = {
    labels: ['Direct', 'Social', 'Referral'],
    datasets: [
      {
        data: [55, 30, 15],
        backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc'],
        hoverBackgroundColor: ['#2e59d9', '#17a673', '#2c9faf'],
        hoverBorderColor: 'rgba(234, 236, 244, 1)',
      },
    ],
  };

  const options = {
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false, // We will build a custom HTML legend below the chart
      },
    },
  };

  return (
    <div className="w-full h-full">
      <Doughnut data={data} options={options} />
    </div>
  );
}