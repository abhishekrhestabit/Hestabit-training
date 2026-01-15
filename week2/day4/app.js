/** * --- UTILITY: DEBOUNCE ---
 * Delays execution until the user stops typing.
 */
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

/** * --- ERROR HANDLING: TOAST NOTIFICATIONS --- 
 */
const toastContainer = document.getElementById('toast-container');

function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'error' ? '⚠️' : '✅';
    
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span>${message}</span>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s ease-out forwards';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// --- STATE MANAGEMENT ---
const STORAGE_KEY = 'day4_todos_v2';
let todos = [];
let filterText = '';

// Load from LocalStorage
function loadTodos() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        todos = stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error("Corrupt data found.", error);
        showToast("Data corrupted. Resetting list.", "error");
        todos = [];
    }
}

// Save to LocalStorage
function saveTodos() {
    try {
        // SIMULATED ERROR: Fails 10% of the time
        if (Math.random() < 0.1) {
            throw new Error("Simulated Storage Failure!");
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
    } catch (error) {
        console.error("Save failed:", error);
        showToast("Failed to save: " + error.message, "error");
    }
}

// --- DOM ELEMENTS ---
const todoList = document.getElementById('todo-list');
const todoInput = document.getElementById('todo-input');
const searchInput = document.getElementById('search-input');
const addBtn = document.getElementById('add-btn');
const clearBtn = document.getElementById('clear-btn');
const errorBtn = document.getElementById('error-btn');
const emptyState = document.getElementById('empty-state');
const countText = document.getElementById('count-text');
const statusText = document.getElementById('status-text');

// --- RENDER LOGIC ---
function render() {
    todoList.innerHTML = '';
    
    const filteredTodos = todos.filter(todo => 
        todo.text.toLowerCase().includes(filterText.toLowerCase())
    );

    const activeCount = todos.filter(t => !t.completed).length;
    countText.textContent = `${activeCount} item${activeCount !== 1 ? 's' : ''} left`;
    
    const date = new Date();
    statusText.textContent = date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

    if (filteredTodos.length === 0) {
        emptyState.classList.add('visible');
    } else {
        emptyState.classList.remove('visible');
    }

    filteredTodos.forEach((todo) => {
        const realIndex = todos.indexOf(todo);

        const li = document.createElement('li');
        li.className = `todo-item ${todo.completed ? 'completed' : ''}`;

        // Checkbox
        const check = document.createElement('div');
        check.className = 'check-circle';
        check.textContent = '✔';
        check.onclick = () => toggleTodo(realIndex);

        // Content
        const content = document.createElement('div');
        content.className = 'todo-text';
        
        if (todo.isEditing) {
            const editInput = document.createElement('input');
            editInput.type = 'text';
            editInput.value = todo.text;
            editInput.className = 'edit-input';
            setTimeout(() => editInput.focus(), 0);
            
            const saveEdit = () => updateTodoText(realIndex, editInput.value);
            editInput.onkeydown = (e) => { if(e.key === 'Enter') saveEdit(); };
            editInput.onblur = saveEdit;
            
            content.appendChild(editInput);
        } else {
            content.textContent = todo.text;
            content.onclick = () => enableEditMode(realIndex);
        }

        // Actions
        const actions = document.createElement('div');
        actions.className = 'actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'icon-btn';
        editBtn.innerHTML = '✏️';
        editBtn.onclick = (e) => { e.stopPropagation(); enableEditMode(realIndex); };

        const delBtn = document.createElement('button');
        delBtn.className = 'icon-btn delete';
        delBtn.innerHTML = '🗑️';
        delBtn.onclick = (e) => { e.stopPropagation(); deleteTodo(realIndex); };

        actions.append(editBtn, delBtn);
        li.append(check, content, actions);
        todoList.appendChild(li);
    });
}

// --- CRUD OPERATIONS ---
function addTodo() {
    try {
        const text = todoInput.value.trim();
        if (!text) {
            showToast("Please enter a task name", "error");
            return;
        }

        todos.push({
            text: text,
            completed: false,
            isEditing: false,
            id: Date.now()
        });

        todoInput.value = '';
        saveTodos();
        render();
    } catch (e) {
        showToast("Unexpected error adding task", "error");
    }
}

function deleteTodo(index) {
    todos.splice(index, 1);
    saveTodos();
    render();
}

function toggleTodo(index) {
    todos[index].completed = !todos[index].completed;
    saveTodos();
    render();
}

function enableEditMode(index) {
    todos.forEach(t => t.isEditing = false);
    todos[index].isEditing = true;
    render();
}

function updateTodoText(index, newText) {
    if (newText.trim()) {
        todos[index].text = newText.trim();
    }
    todos[index].isEditing = false;
    saveTodos();
    render();
}

function clearAll() {
    if(confirm("Are you sure you want to delete all tasks?")) {
        todos = [];
        saveTodos();
        render();
        showToast("All tasks cleared", "success");
    }
}

function simulateRandomError() {
    try {
        const errors = [
            "Network Timeout: Could not sync.",
            "QuotaExceededError: Storage full.",
            "SyntaxError: Unexpected token in JSON."
        ];
        throw new Error(errors[Math.floor(Math.random() * errors.length)]);
    } catch (error) {
        showToast(error.message, "error");
        console.warn("Caught simulated error:", error);
    }
}

// --- EVENT LISTENERS ---
addBtn.addEventListener('click', addTodo);
todoInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') addTodo(); });
clearBtn.addEventListener('click', clearAll);
errorBtn.addEventListener('click', simulateRandomError);
searchInput.addEventListener('input', debounce((e) => {
    filterText = e.target.value;
    render();
}, 300));

// Start
loadTodos();
render();
