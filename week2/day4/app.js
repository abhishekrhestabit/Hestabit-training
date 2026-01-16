
const toastContainer = document.getElementById('toast-container');

function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Lucide icons for Toasts
    const iconHTML = type === 'error' 
        ? '<i data-lucide="alert-circle" style="color:var(--danger)"></i>' 
        : '<i data-lucide="check-circle" style="color:var(--success)"></i>';
    
    toast.innerHTML = `
        <span class="toast-icon">${iconHTML}</span>
        <span>${message}</span>
    `;

    toastContainer.appendChild(toast);

    // Render the new icon
    if (window.lucide) lucide.createIcons();

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s ease-out forwards';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// --- STATE MANAGEMENT ---
const STORAGE_KEY = 'day4_todos_v2';
let todos = [];

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
        localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
    } catch (error) {
        console.error("Save failed:", error);
        showToast("Failed to save: " + error.message, "error");
    }
}

// --- DOM ELEMENTS ---
const todoList = document.getElementById('todo-list');
const todoInput = document.getElementById('todo-input');
const addBtn = document.getElementById('add-btn');
const clearBtn = document.getElementById('clear-btn');
const emptyState = document.getElementById('empty-state');
const countText = document.getElementById('count-text');
const statusText = document.getElementById('status-text');

// --- RENDER LOGIC ---
function render() {
    todoList.innerHTML = '';
    
    const activeCount = todos.filter(t => !t.completed).length;
    countText.textContent = `${activeCount} item${activeCount !== 1 ? 's' : ''} left`;
    
    const date = new Date();
    statusText.textContent = date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

    if (todos.length === 0) {
        emptyState.classList.add('visible');
    } else {
        emptyState.classList.remove('visible');
    }

    todos.forEach((todo) => {
        const realIndex = todos.indexOf(todo);

        const li = document.createElement('li');
        li.className = `todo-item ${todo.completed ? 'completed' : ''}`;

        // Checkbox with Icon
        const check = document.createElement('div');
        check.className = 'check-circle';
        // We put the icon structure here; CSS handles visibility
        check.innerHTML = '<i data-lucide="check"></i>';
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

        // Actions with Icons
        const actions = document.createElement('div');
        actions.className = 'actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'icon-btn';
        editBtn.innerHTML = '<i data-lucide="pencil"></i>';
        editBtn.onclick = (e) => { e.stopPropagation(); enableEditMode(realIndex); };

        const delBtn = document.createElement('button');
        delBtn.className = 'icon-btn delete';
        delBtn.innerHTML = '<i data-lucide="trash-2"></i>';
        delBtn.onclick = (e) => { e.stopPropagation(); deleteTodo(realIndex); };

        actions.append(editBtn, delBtn);
        li.append(check, content, actions);
        todoList.appendChild(li);
    });

    // IMPORTANT: Re-scan the DOM to replace <i> tags with SVGs
    if (window.lucide) {
        lucide.createIcons();
    }
}

// --- CRUD OPERATIONS ---
function addTodo() {
    // [DEBUGGING PRACTICE]
    // The 'debugger' keyword forces a Breakpoint here if DevTools (F12) is open.
    // This allows you to inspect variables like 'text' before the logic runs.
    debugger; 

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

// --- EVENT LISTENERS ---
addBtn.addEventListener('click', addTodo);
todoInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') addTodo(); });
clearBtn.addEventListener('click', clearAll);

// Start
loadTodos();
// Initial render (and icon creation)
render();
