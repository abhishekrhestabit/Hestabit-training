 // --- APP STATE ---
        let inventory = [];
        let cart = JSON.parse(localStorage.getItem('os_cart')) || [];
        let activeCat = 'all';
        let slideIdx = 0;
        let isDarkMode = localStorage.getItem('os_theme') !== 'light'; // Default to dark

        // --- SCROLL ANIMATION OBSERVER ---
        const observerOptions = {
            threshold: 0.1,
            rootMargin: "0px 0px -50px 0px"
        };
        const scrollObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if(entry.isIntersecting) {
                    entry.target.classList.add('active');
                    scrollObserver.unobserve(entry.target); // Animate only once
                }
            });
        }, observerOptions);

        // --- ELEMENTS ---
        const views = { home: document.getElementById('view-home'), shop: document.getElementById('view-shop') };
        const els = {
            shopGrid: document.getElementById('shopGrid'),
            ratedGrid: document.getElementById('topRatedGrid'),
            cartList: document.getElementById('cartList'),
            search: document.getElementById('searchProduct'),
            sort: document.getElementById('sortSort'),
            dropdown: document.getElementById('catDropdown'),
            shopTitle: document.getElementById('shopPageTitle'),
            cartBadge: document.getElementById('cartBadge'),
            cartHeaderCount: document.getElementById('cartCountHeader'),
            cartTotal: document.getElementById('cartTotalDisplay'),
            emptyMsg: document.getElementById('emptyMsg'),
            themeBtn: document.getElementById('themeBtn')
        };

        // --- INIT ---
        async function init() {
            // Apply Theme
            applyTheme();
            
            updateCartUI();
            startSlider();
            if(window.lucide) lucide.createIcons();

            try {
                // Fetch ample data to ensure we find matching categories
                const res = await fetch('https://dummyjson.com/products?limit=190');
                const data = await res.json();
                inventory = data.products;

                // 1. Dynamic Bento Images (Highest rated item in category)
                setBestImage('laptops', 'bento-laptop-img');
                setBestImage('home-decoration', 'bento-decor-img');

                renderDropdown(inventory);
                renderHomeRated(inventory);
                renderShop(inventory); // Pre-load shop

                // Observe initial static elements
                document.querySelectorAll('.reveal').forEach(el => scrollObserver.observe(el));

            } catch(e) {
                console.error(e);
                els.shopGrid.innerHTML = '<p style="color:red; text-align:center">Error loading products. Please check connection.</p>';
            }
        }

        // --- THEME LOGIC ---
        window.toggleTheme = () => {
            isDarkMode = !isDarkMode;
            localStorage.setItem('os_theme', isDarkMode ? 'dark' : 'light');
            applyTheme();
        };

        function applyTheme() {
            if (isDarkMode) {
                document.documentElement.removeAttribute('data-theme');
                els.themeBtn.innerHTML = '<i data-lucide="moon" style="width:20px;"></i>';
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                els.themeBtn.innerHTML = '<i data-lucide="sun" style="width:20px;"></i>';
            }
            if(window.lucide) lucide.createIcons();
        }

        // Helper to find highest rated image for Bento Grid
        function setBestImage(catName, imgId) {
            const items = inventory.filter(p => p.category === catName);
            if (items.length > 0) {
                items.sort((a, b) => b.rating - a.rating); // Sort high to low
                const imgEl = document.getElementById(imgId);
                if(imgEl) {
                    imgEl.src = items[0].thumbnail;
                }
            } else {
                console.warn(`No items found for category: ${catName}`);
                // Fallback images if API category names changed
                if(catName === 'laptops') document.getElementById(imgId).src = 'https://cdn.dummyjson.com/products/images/laptops/MacBook%20Pro/thumbnail.png';
            }
        }

        // --- NAVIGATION ---
        window.navigateTo = (view, cat) => {
            // Toggle Views
            Object.values(views).forEach(el => el.classList.add('hidden'));
            views[view].classList.remove('hidden');
            
            // Scroll top
            window.scrollTo({ top: 0, behavior: 'smooth' });

            // Nav link active states
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            if(view === 'home') document.querySelector('.nav-link[onclick*="home"]').classList.add('active');
            if(view === 'shop') document.querySelector('.nav-link[onclick*="shop"]').classList.add('active');

            if(view === 'shop') {
                if(cat) filterCategory(cat);
                else if(activeCat === 'all') renderShop(inventory);
            }
            if(window.lucide) lucide.createIcons();
            
            // Re-trigger animations for new view content
            setTimeout(() => {
                document.querySelectorAll('.reveal:not(.active)').forEach(el => scrollObserver.observe(el));
            }, 100);
        }

        window.toggleCart = () => {
            document.getElementById('cartSidebar').classList.toggle('open');
            document.getElementById('cartOverlay').classList.toggle('open');
        };

        // --- SLIDER ---
        function startSlider() {
            const imgs = document.querySelectorAll('.hero-img');
            setInterval(() => {
                imgs[slideIdx].classList.remove('active');
                slideIdx = (slideIdx + 1) % imgs.length;
                imgs[slideIdx].classList.add('active');
            }, 5000);
        }

        // --- RENDERING ---
        function renderDropdown(products) {
            // Get ALL unique categories and sort them
            const cats = [...new Set(products.map(p => p.category))].sort();

            els.dropdown.innerHTML = `<span class="dropdown-item" onclick="navigateTo('shop', 'all')">All Products</span>`;
            
            // Render every category found in the data
            cats.forEach(c => {
                const link = document.createElement('span');
                link.className = 'dropdown-item';
                link.textContent = formatTxt(c);
                link.onclick = (e) => { e.preventDefault(); navigateTo('shop', c); };
                els.dropdown.appendChild(link);
            });
        }

        function renderHomeRated(products) {
            // Get strictly high rated items for "AI Picks"
            const top = products.filter(p => p.rating >= 4.7).slice(0, 4);
            els.ratedGrid.innerHTML = '';
            top.forEach(p => {
                const card = createProductCard(p);
                card.classList.add('reveal'); // Add animation class
                els.ratedGrid.appendChild(card);
                scrollObserver.observe(card); // Observe
            });
            if(window.lucide) lucide.createIcons();
        }

        function renderShop(products) {
            els.shopGrid.innerHTML = '';
            if(products.length === 0) {
                els.emptyMsg.classList.remove('hidden');
            } else {
                els.emptyMsg.classList.add('hidden');
                products.forEach(p => {
                    const card = createProductCard(p);
                    card.classList.add('reveal'); // Add animation class
                    els.shopGrid.appendChild(card);
                    scrollObserver.observe(card); // Observe
                });
            }
            if(window.lucide) lucide.createIcons();
        }

        function createProductCard(p) {
            const div = document.createElement('div');
            div.className = 'product-card';
            
            // Generate Stars
            const starsHTML = getStarRatingHTML(p.rating);

            div.innerHTML = `
                <div class="p-img-container">
                    <img src="${p.thumbnail}" class="p-img" loading="lazy" alt="${p.title}">
                </div>
                <div class="p-info">
                    <div class="p-cat">${formatTxt(p.category)}</div>
                    <h3>${p.title}</h3>
                    <div class="p-rating">
                        ${starsHTML} <span style="color:var(--text-muted); margin-left:4px;">(${p.rating})</span>
                    </div>
                    <div class="p-footer">
                        <span class="p-price">$${p.price}</span>
                        <button class="btn-add" onclick="addToCart(${p.id})"><i data-lucide="plus" style="width:20px;"></i></button>
                    </div>
                </div>
            `;
            return div;
        }

        function getStarRatingHTML(rating) {
            const fullStar = `<svg class="star-icon" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path></svg>`;
            const emptyStar = `<svg class="star-icon star-muted" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path></svg>`;
            
            let html = '';
            const rounded = Math.round(rating);
            for(let i=1; i<=5; i++) {
                html += i <= rounded ? fullStar : emptyStar;
            }
            return html;
        }

        // --- FILTER & LOGIC ---
        window.filterCategory = (cat, btn) => {
            activeCat = cat;
            if(btn) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            } else {
                // If called from nav, update tabs manually
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                const matchingBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => 
                    b.innerText.toLowerCase().includes(cat === 'home-decoration' ? 'furniture' : cat) || 
                    (cat === 'all' && b.innerText === 'All')
                );
                if(matchingBtn) matchingBtn.classList.add('active');
            }
            
            els.shopTitle.textContent = cat === 'all' ? 'All Products' : formatTxt(cat);
            applyFilters();
        };

        function applyFilters() {
            let list = [...inventory];
            
            // Category Logic
            if(activeCat !== 'all') {
                if(activeCat === 'beauty') {
                    list = list.filter(p => ['beauty', 'skin-care', 'fragrances'].includes(p.category));
                } 
                else if (activeCat === 'furniture') {
                    list = list.filter(p => ['furniture', 'home-decoration'].includes(p.category));
                }
                else {
                    list = list.filter(p => p.category === activeCat);
                }
            }

            // Search
            const term = els.search.value.toLowerCase();
            if(term) list = list.filter(p => p.title.toLowerCase().includes(term));

            // Sort
            const sortVal = els.sort.value;
            if(sortVal === 'price_low') list.sort((a,b) => a.price - b.price);
            else if(sortVal === 'price_high') list.sort((a,b) => b.price - a.price);
            else if(sortVal === 'rating') list.sort((a,b) => b.rating - a.rating);

            renderShop(list);
        }

        els.search.addEventListener('input', applyFilters);
        els.sort.addEventListener('change', applyFilters);

        // --- CART ---
        window.addToCart = (id) => {
            const item = inventory.find(p => p.id === id);
            const existing = cart.find(c => c.id === id);
            if(existing) existing.qty++; else cart.push({...item, qty:1});
            updateCartUI();
            
            // Visual feedback
            const btn = document.querySelector(`button[onclick="addToCart(${id})"]`);
            if(btn) {
                const originalHTML = btn.innerHTML;
                btn.style.background = "#3b82f6";
                btn.innerHTML = `<i data-lucide="check" style="width:20px;"></i>`;
                if(window.lucide) lucide.createIcons();
                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                    btn.style.background = "";
                    if(window.lucide) lucide.createIcons();
                }, 1000);
            }
        };

        window.remItem = (id) => {
            cart = cart.filter(c => c.id !== id);
            updateCartUI();
        };

        window.checkout = () => {
            if(cart.length === 0) return;
            alert("Thank you for your purchase! This is a demo store. AI Personalization engine has recorded your preference.");
            cart = [];
            updateCartUI();
            toggleCart();
        };

        function updateCartUI() {
            localStorage.setItem('os_cart', JSON.stringify(cart));
            const count = cart.reduce((a,b) => a+b.qty, 0);
            
            els.cartBadge.innerText = count;
            els.cartHeaderCount.innerText = count;
            els.cartBadge.classList.toggle('hidden', count === 0);

            els.cartList.innerHTML = '';
            let total = 0;

            if(cart.length === 0) {
                els.cartList.innerHTML = `
                    <div style="text-align:center; color:var(--text-muted); padding-top:2rem;">
                        <i data-lucide="shopping-cart" style="width:40px; height:40px; opacity:0.5; margin-bottom:1rem;"></i>
                        <p>Your cart is empty.</p>
                        <button onclick="toggleCart(); navigateTo('shop','all')" style="margin-top:1rem; background:transparent; border:1px solid #333; color:var(--text-main); padding:0.5rem 1rem; border-radius:6px; cursor:pointer;">Start Shopping</button>
                    </div>`;
                if(window.lucide) lucide.createIcons();
            }

            cart.forEach(item => {
                total += item.price * item.qty;
                els.cartList.innerHTML += `
                    <div class="cart-item">
                        <div class="cart-img-box"><img src="${item.thumbnail}" class="cart-img"></div>
                        <div style="flex-grow:1;">
                            <div style="font-weight:600; font-size:1rem; margin-bottom:0.25rem;">${item.title}</div>
                            <div style="font-size:0.9rem; color:var(--text-muted);">$${item.price} x ${item.qty}</div>
                        </div>
                        <button onclick="remItem(${item.id})" style="background:none; border:none; color:#ff4444; cursor:pointer;"><i data-lucide="trash-2" style="width:18px"></i></button>
                    </div>
                `;
            });
            els.cartTotal.innerText = '$' + total.toFixed(2);
            if(window.lucide) lucide.createIcons();
        }

        // Helper
        function formatTxt(str) {
            return str.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ');
        }

        init();