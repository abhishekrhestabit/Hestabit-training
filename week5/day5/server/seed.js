const API_URL = 'http://localhost:5000/api/goals'; // Must match your Backend port

// --- 1. CLEAN FUNCTION ---
async function cleanDB() {
  console.log("🧹 Cleaning old todos...");
  try {
    const res = await fetch(API_URL);
    const todos = await res.json();
    
    for (const todo of todos) {
      await fetch(`${API_URL}/${todo._id}`, { method: 'DELETE' });
    }
    console.log("✨ Database Cleared.\n");
  } catch (err) {
    console.error("⚠️ Cleaning failed (Is server running?):", err.message);
  }
}

// --- 2. CREATE HELPER ---
async function createTodo(title, deadline) {
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, deadline })
    });
    
    const data = await res.json();
    if (!res.ok) throw new Error(data.message);
    
    console.log(`✅ Created: "${title}"`);
    return data._id; 
  } catch (error) {
    console.error(`❌ Failed: ${title} -`, error.message);
  }
}

// --- 3. SEEDING LOGIC ---
async function seed() {
  await cleanDB();
  console.log("🌱 Adding sample todos...\n");

  // Sample todos
  await createTodo("Complete project documentation", "2026-02-15");
  await createTodo("Review pull requests", "2026-02-10");
  await createTodo("Fix bug in authentication module", "2026-02-12");
  await createTodo("Update dependencies to latest versions", "2026-02-20");
  await createTodo("Write unit tests for API endpoints", "2026-02-18");
  await createTodo("Schedule team meeting for sprint planning", "2026-02-11");
  await createTodo("Research new database optimization techniques", "2026-02-25");
  await createTodo("Refactor legacy code in user service", "2026-02-28");
  await createTodo("Deploy staging environment", "2026-02-14");
  await createTodo("Create API documentation", "2026-02-22");

  console.log("\n✨ Sample todos added successfully! Refresh your app.");
}

seed();