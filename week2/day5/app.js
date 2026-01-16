// --- STATE MANAGEMENT ---
let allProducts = [];
let cart = JSON.parse(localStorage.getItem('os_cart')) || []; 
let currentCategory = 'all';

// Map categories to display titles
const categoryTitles = {
    'all': 'New Arrivals',
    'laptops': 'Pro Laptops',
    'beauty': 'Beauty & Skincare',
    'furniture': 'Modern Furniture',
    'groceries': 'Daily Essentials',
    'home-decoration': 'Home Decor'
};

// Define the sections order for the "Shop All" page
const shopSections = [
    { id: 'laptops', title: 'Pro Laptops' },
    { id: 'beauty', title: 'Beauty & Fragrances', group: ['beauty', 'fragrances', 'skin-care', 'skincare'] },
    { id: 'home-decoration', title: 'Home & Decor' },
    { id: 'groceries', title: 'Daily Essentials' }
];

// --- DOM ELEMENTS ---
const container = document.getElementById('productContainer');
const loader = document.getElementById('loader');
const sortSelect = document.getElementById('sortSelect');
const searchInput = document.getElementById('searchInput');
const noResults = document.getElementById('noResults');
const cartSidebar = document.getElementById('cartSidebar');
const cartOverlay = document.getElementById('cartOverlay');
const filterTabs = document.querySelectorAll('.filter-tab');
const navLinks = document.querySelectorAll('.nav-link');
const sectionTitle = document.querySelector('.section-title');
const categoryDropdown = document.getElementById('categoryDropdown');

// --- INITIALIZATION ---
async function init() {
    console.log("App Initializing...");
    
    if (!container || !loader) {
        console.error("Critical: DOM elements not found.");
        return;
    }

    updateCartUI();
    
    try {
        if (window.lucide) lucide.createIcons();
    } catch (iconErr) {
        console.warn("Icons not ready yet");
    }
    
    try {
        console.log("Fetching products...");
        const res = await fetch('https://dummyjson.com/products?limit=100');
        
        if (!res.ok) throw new Error(`HTTP Error! Status: ${res.status}`);

        const data = await res.json();
        allProducts = data.products;
        
        setTimeout(() => {
            loader.classList.add('hidden');
            container.classList.remove('hidden');
            
            // Populate Dynamic Dropdown
            populateDropdown(allProducts);

            // Initial Render
            applyFilters();
            
            if (window.lucide) lucide.createIcons();
        }, 600);

    } catch (err) {
        console.error("Fetch failed:", err);
        loader.classList.add('hidden');
        container.classList.remove('hidden');
        container.innerHTML = `
            <div style="text-align:center; color: #ef4444; grid-column: 1/-1; padding: 2rem;">
                <h3 style="font-size: 1.5rem; margin-bottom: 0.5rem;">Service Unavailable</h3>
                <p>Could not load products. Please check your internet connection.</p>
            </div>`;
    }
}

// --- DYNAMIC DROPDOWN GENERATOR ---
function populateDropdown(products) {
    if (!categoryDropdown) return;

    // 1. Extract unique categories
    const categories = [...new Set(products.map(p => p.category))].sort();
    
    categoryDropdown.innerHTML = ''; // Clear existing

    // 2. Add 'All' link first
    const allLink = document.createElement('a');
    allLink.className = 'dropdown-item';
    allLink.textContent = 'All Products';
    allLink.onclick = (e) => {
        e.preventDefault();
        filterCategory('all');
    };
    categoryDropdown.appendChild(allLink);

    // 3. Create links for each category
    categories.forEach(cat => {
        const item = document.createElement('a');
        item.className = 'dropdown-item';
        // Format: 'skin-care' -> 'Skin Care'
        item.textContent = cat.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
        item.onclick = (e) => {
            e.preventDefault(); // Prevent jump
            filterCategory(cat);
        };
        categoryDropdown.appendChild(item);
    });
}

// --- RENDER HELPERS ---

function createCardHTML(product) {
    const isNew = product.id % 7 === 0 ? `<span class="new-badge">New Arrival</span>` : '';
    const ratingHTML = `<div class="card-rating">${product.rating.toFixed(1)} ★</div>`;
    
    return `
        <div class="os-card fade-in">
            <div class="card-header">
                ${isNew}
                <h3 class="card-title">${product.title}</h3>
                <p class="card-category">${product.category}</p>
            </div>
            <div class="card-image-wrapper">
                 <img src="${product.thumbnail}" class="card-image" alt="${product.title}" loading="lazy">
            </div>
            <div class="card-footer">
                <div class="price-group">
                    <span class="card-price">$${product.price}</span>
                    ${ratingHTML}
                </div>
                <button onclick="addToCart(${product.id})" class="btn-pill">Add</button>
            </div>
        </div>
    `;
}

function renderFlat(products) {
    container.innerHTML = '';
    container.className = 'product-grid'; 
    
    if (!products || products.length === 0) {
        container.classList.add('hidden');
        noResults.classList.remove('hidden');
        return;
    }
    container.classList.remove('hidden');
    noResults.classList.add('hidden');

    products.forEach(product => {
        const div = document.createElement('div');
        div.innerHTML = createCardHTML(product);
        container.appendChild(div.firstElementChild);
    });
}

function renderSections() {
    container.innerHTML = '';
    container.className = 'product-sections-container';
    
    container.classList.remove('hidden');
    noResults.classList.add('hidden');

    shopSections.forEach(section => {
        const sectionProducts = allProducts.filter(p => {
            if (section.group) return section.group.includes(p.category);
            return p.category === section.id;
        });

        if (sectionProducts.length > 0) {
            const sectionWrapper = document.createElement('div');
            sectionWrapper.className = 'category-section';
            
            const titleHTML = `<h2 class="category-section-title">${section.title}</h2>`;
            
            let gridHTML = '<div class="product-grid">';
            sectionProducts.forEach(p => {
                 gridHTML += createCardHTML(p);
            });
            gridHTML += '</div>';

            sectionWrapper.innerHTML = titleHTML + gridHTML;
            container.appendChild(sectionWrapper);
        }
    });
}

// --- CORE FILTER LOGIC ---
function applyFilters() {
    let filtered = [...allProducts];
    const sortValue = sortSelect.value;
    const searchTerm = searchInput.value.toLowerCase().trim();

    // 1. FILTER CATEGORY
    if (currentCategory !== 'all') {
        if(currentCategory === 'beauty') {
             filtered = filtered.filter(p => ['beauty','fragrances','skin-care','skincare'].includes(p.category));
        } else if(currentCategory === 'groceries') {
            filtered = filtered.filter(p => p.category === 'groceries');
        } else {
            filtered = filtered.filter(p => p.category === currentCategory);
        }
    } else {
        filtered = filtered.filter(p => p.category !== 'smartphones');
    }

    // 2. SEARCH FILTER
    if (searchTerm) {
        filtered = filtered.filter(p => p.title.toLowerCase().includes(searchTerm));
    }

    // 3. SORT
    if (sortValue === 'low') filtered.sort((a,b) => a.price - b.price);
    if (sortValue === 'high') filtered.sort((a,b) => b.price - a.price);
    if (sortValue === 'rating') filtered.sort((a,b) => b.rating - a.rating);

    // 4. RENDER DECISION
    if (currentCategory === 'all' && sortValue === 'default' && !searchTerm) {
        renderSections();
    } else {
        renderFlat(filtered);
    }
    
    if (window.lucide) lucide.createIcons();
}

// --- CART LOGIC ---
function addToCart(id) {
    const product = allProducts.find(p => p.id === id);
    const existingItem = cart.find(item => item.id === id);
    if (existingItem) existingItem.qty++;
    else cart.push({ ...product, qty: 1 });
    saveCart();
    updateCartUI();
    if (!cartSidebar.classList.contains('open')) toggleCart();
}

function removeFromCart(id) {
    cart = cart.filter(item => item.id !== id);
    saveCart();
    updateCartUI();
}

function updateQty(id, change) {
    const item = cart.find(p => p.id === id);
    if (item) {
        item.qty += change;
        if (item.qty <= 0) removeFromCart(id);
        else saveCart();
        updateCartUI();
    }
}

function saveCart() { localStorage.setItem('os_cart', JSON.stringify(cart)); }

function updateCartUI() {
    const totalItems = cart.reduce((acc, item) => acc + item.qty, 0);
    const badge = document.getElementById('cartCountBadge');
    if(badge) {
        badge.innerText = totalItems;
        badge.classList.toggle('hidden', totalItems === 0);
    }
    const cartList = document.getElementById('cartItems');
    const cartTotal = document.getElementById('cartTotal');
    const cartFinalTotal = document.getElementById('cartFinalTotal');
    if(cartList) cartList.innerHTML = '';
    let totalPrice = 0;

    if (cart.length === 0) {
        if(cartList) cartList.innerHTML = `<div class="empty-cart-msg"><p>Your bag is empty.</p></div>`;
    } else {
        cart.forEach(item => {
            totalPrice += item.price * item.qty;
            if(cartList) cartList.innerHTML += `
                <div class="cart-item">
                    <img src="${item.thumbnail}" class="cart-item-img" style="width:50px;">
                    <div class="cart-item-info">
                        <h4>${item.title}</h4>
                        <span>$${item.price} x ${item.qty}</span>
                    </div>
                    <button onclick="removeFromCart(${item.id})">x</button>
                </div>`;
        });
    }
    if(cartTotal) cartTotal.innerText = '$' + totalPrice.toFixed(2);
    if(cartFinalTotal) cartFinalTotal.innerText = '$' + totalPrice.toFixed(2);
}

function toggleCart() {
    if(cartSidebar) {
        cartSidebar.classList.toggle('open');
        const isOpen = cartSidebar.classList.contains('open');
        cartOverlay.classList.toggle('hidden', !isOpen);
        document.body.style.overflow = isOpen ? 'hidden' : '';
    }
}

// Event Listeners
sortSelect.addEventListener('change', applyFilters);
searchInput.addEventListener('input', applyFilters);

window.filterCategory = (cat, element) => {
    currentCategory = cat;
    if(element) {
        filterTabs.forEach(t => t.classList.remove('active'));
        element.classList.add('active');
    }
    
    // Dynamic Title Logic
    if(sectionTitle) {
        // Try the map first, otherwise format the slug
        sectionTitle.textContent = categoryTitles[cat] || cat.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    }
    applyFilters();
};

init();