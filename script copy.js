document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // ІНТЕРАКТИВНИЙ КУРСОР (ЕФЕКТ ЗА МИШКОЮ)
    // ==========================================
    // ==========================================
    // МОДЕРНІЗОВАНИЙ ІНТЕРАКТИВНИЙ КУРСОР-ЛІХТАРИК
    // ==========================================
    const glow = document.querySelector('.cursor-glow');
    let mouseTimeout;
    let lastX = 0;
    let lastY = 0;

    window.addEventListener('mousemove', (e) => {
        // Очищуємо попередній таймер зупинки миші
        clearTimeout(mouseTimeout);

        // Розраховуємо швидкість руху миші (відстань між поточним та попереднім положенням)
        const deltaX = e.clientX - lastX;
        const deltaY = e.clientY - lastY;
        const speed = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // Оновлюємо попередні координати для наступного кроку
        lastX = e.clientX;
        lastY = e.clientY;

        // Обмеження на максимальний масштаб та яскравість підсвічування при швидкому русі
        const scaleFactor = Math.min(0.8 + speed * 0.015, 1.3);
        const opacityFactor = Math.min(speed * 0.05, 1); // Наростає від руху, максимум 1

        // Передаємо значення в CSS-змінні
        glow.style.setProperty('--x', `${e.clientX}px`);
        glow.style.setProperty('--y', `${e.clientY}px`);
        glow.style.setProperty('--scale', scaleFactor);
        glow.style.setProperty('--opacity', opacityFactor);

        // Таймер, який спрацьовує, коли користувач зупиняє або суттєво уповільнює мишу
        mouseTimeout = setTimeout(() => {
            glow.style.setProperty('--opacity', '0');
            glow.style.setProperty('--scale', '0.7');
        }, 150); // Час у мілісекундах до початку плавного згасання
    });

    // ==========================================
    // ЛОГІКА МИТТЄВОГО ПЕРЕКЛАДУ (UA / EN)
    // ==========================================
    const langToggleBtn = document.getElementById('lang-toggle');
    let currentLang = 'ua'; // Початкова мова

    const translatableElements = document.querySelectorAll('[data-ua]');

    langToggleBtn.addEventListener('click', () => {
        if (currentLang === 'ua') {
            currentLang = 'en';
            langToggleBtn.textContent = 'UA';
        } else {
            currentLang = 'ua';
            langToggleBtn.textContent = 'EN';
        }

        // Перемикаємо текст для кожного елемента на основі data-атрибутів
        translatableElements.forEach(el => {
            if (currentLang === 'en') {
                el.textContent = el.getAttribute('data-en');
                // Якщо елемент є полем вводу (placeholder)
                if(el.placeholder) el.placeholder = el.getAttribute('data-en');
            } else {
                el.textContent = el.getAttribute('data-ua');
                if(el.placeholder) el.placeholder = el.getAttribute('data-ua');
            }
        });
    });

    // ==========================================
    // ПІДСВІЧУВАННЯ АКТИВНОЇ ВКЛАДКИ ПРИ СКРОЛІ
    // ==========================================
    const sections = document.querySelectorAll('section');
    const navItems = document.querySelectorAll('.nav-links a');

    window.addEventListener('scroll', () => {
        let currentActive = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (pageYOffset >= sectionTop - 200) {
                currentActive = section.getAttribute('id');
            }
        });

        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('href') === `#${currentActive}`) {
                item.classList.add('active');
            }
        });
    });
});

// ==========================================
// КЕРУВАННЯ СТОРІНКАМИ ПРОЄКТІВ (OPEN / CLOSE)
// ==========================================
function openProjectModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Забороняємо скрол основного сайту
    }
}

function closeProjectModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = ''; // Повертаємо скрол
    }
}