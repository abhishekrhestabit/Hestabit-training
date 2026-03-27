import React, { useState, useEffect } from 'react';
function App() {
  const [todos, setTodos] = useState([]);
  const [title, setTitle] = useState('');
  useEffect(() => { fetch('/api/todos').then(r => r.json()).then(setTodos) }, []);
  const add = async () => {
    const res = await fetch('/api/todos', { method: 'POST', body: JSON.stringify({title}), headers: {'Content-Type': 'application/json'} });
    if (res.ok) window.location.reload();
  };
  return (<div><input value={title} onChange={e => setTitle(e.target.value)} /><button onClick={add}>Add</button>
    <ul>{todos.map(t => <li key={t.id}>{t.title}</li>)}</ul></div>);
}
export default App;
