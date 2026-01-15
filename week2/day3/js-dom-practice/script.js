//  1. DATA 
const faqData = [
    {
        id: 1,
        question: "What is the DOM?",
        answer: "The <b>Document Object Model (DOM)</b> is a tree-structure representation of the HTML document. It allows JavaScript to access, modify, and delete elements on the page dynamically.",
        likes: 0,
        dislikes: 0
    },
    {
        id: 2,
        question: "How does this accordion work?",
        answer: "It uses <b>Event Listeners</b> to detect clicks. When you click a header, JavaScript calculates the height of the hidden content (`scrollHeight`) and applies it as an inline style to create a smooth opening animation.",
        likes: 12,
        dislikes: 2
    },
    {
        id: 3,
        question: "Why use max-height for animation?",
        answer: "CSS cannot animate height from <code>0</code> to <code>auto</code>. By setting a specific pixel value to <code>max-height</code> via JavaScript, we force the browser to calculate the transition steps.",
        likes: 5,
        dislikes: 0
    },
    {
        id: 4,
        question: "What is Vanilla CSS?",
        answer: "Vanilla CSS refers to writing standard CSS code without using frameworks like Bootstrap or Tailwind. It gives you complete control over your styles but requires writing more lines of code manually.",
        likes: 8,
        dislikes: 1
    }
];

// 2. DOM ELEMENTS 
const container = document.getElementById('accordion-container');
const sortSelect = document.getElementById('sort-select');
const themeToggle = document.getElementById('theme-toggle');
const modal = document.getElementById('feedback-modal');
const closeModalBtn = document.getElementById('close-modal-btn');

// 3. RENDER FUNCTION 
function renderFAQ(data) {
    container.innerHTML = '';

    data.forEach(item => {
        // Create Item Wrapper
        const itemDiv = document.createElement('div');
        itemDiv.className = 'accordion-item';

        // Create Header Button
        const btn = document.createElement('button');
        btn.className = 'accordion-trigger';
        btn.innerHTML = `
            <span>${item.question}</span>
            <i data-lucide="chevron-down" class="icon-chevron"></i>
        `;

        // Create Content Wrapper
        const contentDiv = document.createElement('div');
        contentDiv.className = 'accordion-content';
        
        contentDiv.innerHTML = `
            <div class="content-inner">
                <p>${item.answer}</p>
                <div class="like-container">
                    <span class="like-text">Was this helpful?</span>
                    
                    <div class="vote-actions">
                        <!-- Dislike Group -->
                        <div style="display: flex; align-items: center;">
                            <button class="btn-vote btn-dislike" title="Not Helpful">
                                <i data-lucide="thumbs-down"></i>
                            </button>
                            <span class="like-count dislike-display" style="font-size: 0.8em; margin-left: 4px; color: #6b7280;">${item.dislikes}</span>
                        </div>

                        <!-- Divider -->
                        <div style="width: 1px; height: 16px; background: #e5e7eb; margin: 0 8px;"></div>
                        
                        <!-- Like Group -->
                        <div style="display: flex; align-items: center;">
                            <span class="like-count like-display" style="font-size: 0.8em; margin-right: 4px; color: #6b7280;">${item.likes}</span>
                            <button class="btn-vote btn-like" title="Helpful">
                                <i data-lucide="heart"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Append to DOM
        itemDiv.appendChild(btn);
        itemDiv.appendChild(contentDiv);
        container.appendChild(itemDiv);

        // EVENT LISTENERS 
        
        // A. Accordion Toggle
        btn.addEventListener('click', () => {
            const isOpen = contentDiv.classList.contains('open');

            // Close ALL others
            document.querySelectorAll('.accordion-content').forEach(el => {
                el.style.maxHeight = null;
                el.classList.remove('open');
            });
            document.querySelectorAll('.accordion-trigger').forEach(el => {
                el.classList.remove('active');
            });

            // Open THIS one if it wasn't open
            if (!isOpen) {
                btn.classList.add('active');
                contentDiv.classList.add('open');
                contentDiv.style.maxHeight = contentDiv.scrollHeight + "px";
            }
        });

        // B. Vote Logic (Closures)
        const likeBtn = contentDiv.querySelector('.btn-like');
        const dislikeBtn = contentDiv.querySelector('.btn-dislike');
        const likeDisplay = contentDiv.querySelector('.like-display');
        const dislikeDisplay = contentDiv.querySelector('.dislike-display');

        // LIKE Listener
        likeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            item.likes++;
            likeDisplay.textContent = item.likes;
            likeBtn.classList.add('liked');
            const svg = likeBtn.querySelector('svg');
            if(svg) {
                svg.classList.add('animate-pop');
                setTimeout(() => svg.classList.remove('animate-pop'), 300);
            }
            showModal();
        });

        // DISLIKE Listener
        dislikeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            item.dislikes++; 
            dislikeDisplay.textContent = item.dislikes;
            const svg = dislikeBtn.querySelector('svg');
            if(svg) {
                svg.classList.add('animate-shake');
                setTimeout(() => svg.classList.remove('animate-shake'), 300);
            }
        });
    });

    lucide.createIcons();
}

// 4. MODAL LOGIC 
function showModal() {
    modal.classList.add('show');
}

function closeModal() {
    modal.classList.remove('show');
}

closeModalBtn.addEventListener('click', closeModal);
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// 5. THEME TOGGLE 
themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark');
    const isDark = document.body.classList.contains('dark');
    
    if (isDark) {
        document.querySelector('[data-lucide="sun"]').style.display = 'block';
        document.querySelector('[data-lucide="moon"]').style.display = 'none';
    } else {
        document.querySelector('[data-lucide="sun"]').style.display = 'none';
        document.querySelector('[data-lucide="moon"]').style.display = 'block';
    }
    lucide.createIcons();
});

// 6. SORT LOGIC 
sortSelect.addEventListener('change', (e) => {
    const value = e.target.value;

    if (value === 'likes') {
        // Sort by Likes (Highest first)
        const sorted = [...faqData].sort((a,b) => b.likes - a.likes);
        renderFAQ(sorted);
    } 
    else if (value === 'dislikes') {
        // Sort by Dislikes (Highest first)
        const sorted = [...faqData].sort((a,b) => b.dislikes - a.dislikes);
        renderFAQ(sorted);
    } 
    else {
        // Default Order (Original Array)
        renderFAQ(faqData);
    }
});

// INIT 
renderFAQ(faqData);
document.querySelector('[data-lucide="sun"]').style.display = 'none';