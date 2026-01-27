"use client";
import { Line } from 'react-chartjs-2';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend,
} from 'chart.js';


const chartOptions = {
  maintainAspectRatio: false,
  responsive: true,}
// 1. Register the Chart.js modules
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend
);

export default function AreaChart() {
  // 2. Define the Data
  const data = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    datasets: [
      {
        label: 'Earnings',
        data: [0, 10000, 5000, 15000, 10000, 20000, 15000, 25000, 20000, 30000, 25000, 40000],
        fill: true, // This creates the "Area" effect under the line
        backgroundColor: 'rgba(78, 115, 223, 0.05)', // Light blue fill
        borderColor: '#4e73df', // Solid blue line
        tension: 0.3, // Makes the line curved (0 is straight, 1 is super curvy)
        pointRadius: 3,
        pointBackgroundColor: '#4e73df',
        pointBorderColor: '#4e73df',
        pointHoverRadius: 3,
        pointHoverBackgroundColor: '#4e73df',
        pointHoverBorderColor: '#4e73df',
        pointHitRadius: 10,
        pointBorderWidth: 2,
      },
    ],
  };

  // 3. Define the Options (to replicate SB Admin style)
  

  return (
    <div className="w-full  h-full flex items-center justify-center">
      <Line data={data} options={chartOptions} />
    </div>
  );
}