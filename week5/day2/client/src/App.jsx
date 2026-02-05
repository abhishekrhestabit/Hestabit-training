import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [data, setData] = useState(null);

  useEffect(() => {
    // We fetch from localhost:5000 because that's where Docker exposes the server
    fetch('http://localhost:5000/api')
      .then(res => res.json())
      .then(result => setData(result))
      .catch(err => console.error("Error fetching data:", err));
  }, []);

  return (
    <div className="App">
      <h1>Docker Multi-Container App</h1>
      <div className="card">
        <h2>Backend Status:</h2>
        {data ? (
          <p style={{color: 'green', fontWeight: 'bold'}}>{data.message}</p>
        ) : (
          <p style={{color: 'red'}}>Connecting to server...</p>
        )}
      </div>
    </div>
  )
}

export default App