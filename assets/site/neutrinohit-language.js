(function () {
  const sections = [
    { key: 'home', ruText: 'Главная', enText: 'Home', ruHref: '/ru/', enHref: '/en/' },
    { key: 'research', ruText: 'Наука', enText: 'Research', ruHref: '/ru/research.html', enHref: '/en/research.html' },
    { key: 'education', ruText: 'Образование', enText: 'Education', ruHref: '/ru/education.html', enHref: '/en/education.html' },
    { key: 'outreach', ruText: 'Научная коммуникация', enText: 'Outreach', ruHref: '/ru/outreach.html', enHref: '/en/outreach.html' },
    { key: 'materials', ruText: 'Материалы', enText: 'Materials', ruHref: '/ru/materials.html', enHref: '/en/materials.html' },
    { key: 'people', ruText: 'Люди', enText: 'People', ruHref: '/ru/people.html', enHref: '/en/people.html' },
    { key: 'about', ruText: 'Обо мне', enText: 'About', ruHref: '/ru/about.html', enHref: '/en/about.html' }
  ];

  const ruLanguageCodes = new Set(['ru', 'be', 'uk', 'kk', 'ky', 'uz', 'tg', 'tk', 'hy', 'az', 'ka', 'ro', 'mo']);
  const pathname = window.location.pathname;
  const activeLanguage = pathname.includes('/en/') ? 'en' : pathname.includes('/ru/') ? 'ru' : null;

  function currentSectionKey() {
    const filename = pathname.split('/').pop() || 'index.html';
    if (filename === 'index.html' || pathname.endsWith('/ru/') || pathname.endsWith('/en/')) return 'home';
    const slug = filename.replace(/\.html$/, '');
    return sections.some((section) => section.key === slug) ? slug : 'home';
  }

  function rememberLanguage(language) {
    try {
      window.localStorage.setItem('neutrinohit-language', language);
    } catch (error) {
      // localStorage can be unavailable in strict privacy modes.
    }
  }

  function storedLanguage() {
    try {
      return window.localStorage.getItem('neutrinohit-language');
    } catch (error) {
      return null;
    }
  }

  function preferredLanguage() {
    const stored = storedLanguage();
    if (stored === 'ru' || stored === 'en') return stored;
    const languages = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    return languages.some((language) => ruLanguageCodes.has(String(language).toLowerCase().split('-')[0])) ? 'ru' : 'en';
  }

  function updateNavbar() {
    if (!activeLanguage) return;
    const key = currentSectionKey();
    const target = activeLanguage === 'en' ? 'en' : 'ru';
    const navLinks = document.querySelectorAll('.navbar a.nav-link');

    navLinks.forEach((link) => {
      const label = link.textContent.trim();
      const section = sections.find((item) => label === item.ruText || label === item.enText);
      if (!section) return;
      link.textContent = target === 'en' ? section.enText : section.ruText;
      link.href = target === 'en' ? section.enHref : section.ruHref;
    });

    document.querySelectorAll('.navbar a.nav-link').forEach((link) => {
      const label = link.textContent.trim();
      if (label !== 'RU' && label !== 'EN') return;
      const section = sections.find((item) => item.key === key) || sections[0];
      link.href = label === 'RU' ? section.ruHref : section.enHref;
      link.addEventListener('click', () => rememberLanguage(label.toLowerCase()));
    });

    rememberLanguage(activeLanguage);
  }

  function updateLandingSuggestion() {
    const suggestion = document.querySelector('[data-language-suggestion]');
    if (!suggestion) return;

    const language = preferredLanguage();
    suggestion.hidden = false;
    suggestion.textContent = language === 'ru'
      ? 'Предложение по языку браузера: начать с русской версии. Переключиться можно в любой момент.'
      : 'Suggested from your browser language: start with the English version. You can switch at any time.';

    document.querySelectorAll('[data-language-choice]').forEach((choice) => {
      choice.classList.toggle('is-suggested', choice.getAttribute('data-language-choice') === language);
      choice.addEventListener('click', () => rememberLanguage(choice.getAttribute('data-language-choice')));
    });
  }

  updateNavbar();
  updateLandingSuggestion();
})();
