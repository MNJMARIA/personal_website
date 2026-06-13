document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // ДИНАМІЧНИЙ ЛІХТАРИК ЗА МИШКОЮ (ЗГАСАННЯ ТА НАРОСТАННЯ)
    // ==========================================
    const glow = document.querySelector('.cursor-glow');
    let mouseTimeout;
    let lastX = 0; let lastY = 0;

    window.addEventListener('mousemove', (e) => {
        clearTimeout(mouseTimeout);
        const deltaX = e.clientX - lastX;
        const deltaY = e.clientY - lastY;
        const speed = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        lastX = e.clientX; lastY = e.clientY;

        const scaleFactor = Math.min(0.8 + speed * 0.015, 1.3);
        const opacityFactor = Math.min(speed * 0.05, 1);

        glow.style.setProperty('--x', `${e.clientX}px`);
        glow.style.setProperty('--y', `${e.clientY}px`);
        glow.style.setProperty('--scale', scaleFactor);
        glow.style.setProperty('--opacity', opacityFactor);

        mouseTimeout = setTimeout(() => {
            glow.style.setProperty('--opacity', '0');
            glow.style.setProperty('--scale', '0.7');
        }, 150);
    });

    // ==========================================
    // ПОЯВА ЕЛЕМЕНТІВ ПРИ СКРОЛІ (SCROLL REVEAL EFFECT)
    // ==========================================
    const revealElements = document.querySelectorAll('.reveal');
    
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, { threshold: 0.15 }); // Елемент з'явиться, коли його видно на 15%

    revealElements.forEach(el => revealObserver.observe(el));

    // ==========================================
    // ЛОГІКА 3D КАРУСЕЛІ СКРИНШОТІВ (РУЛЕТКА)
    // ==========================================
    const setupsCarousel = (container) => {
        const track = container.querySelector('.carousel-track');
        const prevBtn = container.querySelector('.prev-btn');
        const nextBtn = container.querySelector('.next-btn');
        
        if (!track || !prevBtn || !nextBtn) return;

        // Оновлення класів для 3D позиціонування
        const updateCarouselStyles = () => {
            const slides = Array.from(track.children);
            slides.forEach(slide => {
                slide.classList.remove('active-slide', 'next-slide', 'prev-slide');
            });

            // Перший слайд — активний (по центру)
            slides[0].classList.add('active-slide');
            // Другий слайд — наступний (праворуч)
            if (slides[1]) slides[1].classList.add('next-slide');
            // Останній слайд — попередній (ліворуч на задньому плані)
            if (slides.length > 2) slides[slides.length - 1].classList.add('prev-slide');
        };

        // Клік "Вперед" (Зсуваємо масив: перший елемент йде в кінець)
        nextBtn.addEventListener('click', () => {
            const firstChild = track.firstElementChild;
            track.appendChild(firstChild);
            updateCarouselStyles();
        });

        // Клік "Назад" (Останній елемент йде на початок)
        prevBtn.addEventListener('click', () => {
            const lastChild = track.lastElementChild;
            track.insertBefore(lastChild, track.firstElementChild);
            updateCarouselStyles();
        });

        // Ініціалізація початкового стану
        updateCarouselStyles();
    };

    // Запускаємо карусель для кожного блоку окремо
    document.querySelectorAll('.carousel-container').forEach(setupsCarousel);

    // ==========================================
    // МИТТЄВИЙ ПЕРЕКЛАД МОВИ (UA / EN)
    // ==========================================
    const langToggleBtn = document.getElementById('lang-toggle');
    let currentLang = 'ua';
    const translatableElements = document.querySelectorAll('[data-ua]');

    langToggleBtn.addEventListener('click', () => {
        currentLang = (currentLang === 'ua') ? 'en' : 'ua';
        langToggleBtn.textContent = (currentLang === 'ua') ? 'EN' : 'UA';

        translatableElements.forEach(el => {
            el.textContent = el.getAttribute(`data-${currentLang}`);
            if(el.placeholder) el.placeholder = el.getAttribute(`data-${currentLang}`);
        });
    });
});

// ==========================================
// УПРАВЛІННЯ ОКРЕМІМИ СТОРІНКАМИ ПРОЄКТІВ
// ==========================================
function openProjectPage(pageId) {
    const page = document.getElementById(pageId);
    if (page) {
        page.classList.add('active');
        document.body.style.overflow = 'hidden'; // Фіксуємо задній фон
    }
}

function closeProjectPage(pageId) {
    const page = document.getElementById(pageId);
    if (page) {
        page.classList.remove('active');
        document.body.style.overflow = ''; // Повертаємо скрол основного сайту
    }
}

// ==========================================
// ЛОГІКА МОБІЛЬНОГО ПОВНОЕКРАННОГО МЕНЮ
// ==========================================
const menuTrigger = document.getElementById('mobile-menu-trigger');
const mobileOverlay = document.getElementById('mobile-overlay-menu');

function toggleMobileMenu() {
    menuTrigger.classList.toggle('open');
    mobileOverlay.classList.toggle('open');
    
    // Блокуємо скрол основного сайту під час відкритого меню
    if (mobileOverlay.classList.contains('open')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
}

// Прив'язуємо подію кліку до нашої кнопки
menuTrigger.addEventListener('click', toggleMobileMenu);


// ==========================================
// ТОЧНЕ ПІДСВІЧУВАННЯ АКТИВНОЇ ВКЛАДКИ В МЕНЮ
// ==========================================
const sections = document.querySelectorAll('section');
const navItems = document.querySelectorAll('.nav-links a');

window.addEventListener('scroll', () => {
    let currentActive = 'home'; // За замовчуванням активна Головна
    let minDistance = Infinity;

    sections.forEach(section => {
        const rect = section.getBoundingClientRect();
        
        // Шукаємо секцію, верхня межа якої найближче до верху екрану (до координати 150px)
        const distanceToTop = Math.abs(rect.top - 150);
        
        if (distanceToTop < minDistance && rect.bottom > 200) {
            minDistance = distanceToTop;
            currentActive = section.getAttribute('id');
        }
    });

    // Оновлюємо класи для десктопного меню
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === `#${currentActive}`) {
            item.classList.add('active');
        }
    });
});