(function () {
  const sections = [
    { key: 'home', ruText: 'Главная', enText: 'Home', ruHref: '/ru/', enHref: '/en/' },
    { key: 'research', ruText: 'Наука', enText: 'Research', ruHref: '/ru/research.html', enHref: '/en/research.html' },
    { key: 'education', ruText: 'Образование', enText: 'Education', ruHref: '/ru/education.html', enHref: '/en/education.html' },
    { key: 'outreach', ruText: 'Научная коммуникация', enText: 'Outreach', ruHref: '/ru/outreach.html', enHref: '/en/outreach.html' },
    { key: 'materials', ruText: 'Книги', enText: 'Books', ruHref: '/ru/materials.html', enHref: '/en/materials.html' },
    { key: 'modeling', ruText: 'Моделирование', enText: 'Modeling', ruHref: '/ru/modeling.html', enHref: '/en/modeling.html' },
    { key: 'photos-cinema', ruText: 'Фото и кино', enText: 'Photos and Cinema', ruHref: '/ru/photos-cinema.html', enHref: '/en/photos-cinema.html' },
    { key: 'school', ruText: 'Школа', enText: 'School', ruHref: '/ru/school.html', enHref: '/en/school.html' },
    { key: 'about', ruText: 'Обо мне', enText: 'About', ruHref: '/ru/about.html', enHref: '/en/about.html' },
    { key: 'books', ruText: 'Книги', enText: 'Books', ruHref: '/books.html', enHref: '/en/books.html' },
    { key: 'lectures', ruText: 'Лекции', enText: 'Lectures', ruHref: '/lectures.html', enHref: '/en/lectures.html' },
    { key: 'students', ruText: 'Студенты', enText: 'Students', ruHref: '/students.html', enHref: '/en/students.html' },
    { key: 'theses', ruText: 'Диссертации', enText: 'Theses', ruHref: '/theses.html', enHref: '/en/theses.html' },
    { key: 'schools', ruText: 'Школы', enText: 'Schools', ruHref: '/schools.html', enHref: '/en/schools.html' },
    { key: 'talks', ruText: 'Доклады', enText: 'Talks', ruHref: '/talks.html', enHref: '/en/talks.html' },
    { key: 'interviews', ruText: 'Интервью', enText: 'Interviews', ruHref: '/interviews.html', enHref: '/en/interviews.html' },
    { key: 'photos', ruText: 'Фото', enText: 'Photos', ruHref: '/photos.html', enHref: '/en/photos.html' },
    { key: 'sciencepop', ruText: 'Научно-популярные лекции', enText: 'Popular Science', ruHref: '/sciencepop.html', enHref: '/en/sciencepop.html' },
    { key: 'cinema', ruText: 'Мое кино', enText: 'Films', ruHref: '/cinema.html', enHref: '/en/cinema.html' },
    { key: 'animations', ruText: 'Анимации', enText: 'Animations', ruHref: '/animations.html', enHref: '/en/animations.html' },
    { key: 'software', ruText: 'Код', enText: 'Code', ruHref: '/software.html', enHref: '/en/software.html' }
  ];

  const ruLanguageCodes = new Set(['ru', 'be', 'uk', 'kk', 'ky', 'uz', 'tg', 'tk', 'hy', 'az', 'ka', 'ro', 'mo']);
  const pathname = window.location.pathname;

  function currentSectionKey() {
    const filename = pathname.split('/').pop() || 'index.html';
    if (filename === 'index.html' || pathname.endsWith('/ru/') || pathname.endsWith('/en/')) return 'home';
    const slug = filename.replace(/\.html$/, '');
    return sections.some((section) => section.key === slug) ? slug : 'home';
  }

  function detectedLanguage() {
    if (pathname.includes('/en/')) return 'en';
    if (pathname.includes('/ru/')) return 'ru';

    const filename = pathname.split('/').pop() || 'index.html';
    const slug = filename.replace(/\.html$/, '');
    return slug !== 'index' && sections.some((section) => section.key === slug) ? 'ru' : null;
  }

  const activeLanguage = detectedLanguage();

  function fileSiteRootParts() {
    const parts = pathname.split('/').filter(Boolean);
    const languageIndex = Math.max(parts.lastIndexOf('en'), parts.lastIndexOf('ru'));
    if (languageIndex >= 0) return parts.slice(0, languageIndex);

    const siteIndex = parts.lastIndexOf('_site');
    if (siteIndex >= 0) return parts.slice(0, siteIndex + 1);

    return parts.slice(0, -1);
  }

  function relativeHref(fromParts, toParts) {
    let common = 0;
    while (fromParts[common] && fromParts[common] === toParts[common]) common += 1;

    const up = fromParts.slice(common).map(() => '..');
    const down = toParts.slice(common);
    return up.concat(down).join('/') || './';
  }

  function siteHref(href) {
    if (window.location.protocol !== 'file:' || !href.startsWith('/')) return href;

    const match = href.match(/^([^?#]*)([?#].*)?$/);
    const rawPath = match ? match[1] : href;
    const suffix = match && match[2] ? match[2] : '';
    const targetPath = rawPath.endsWith('/') ? `${rawPath}index.html` : rawPath;
    const currentParts = pathname.split('/').filter(Boolean);
    const currentDirParts = pathname.endsWith('/') ? currentParts : currentParts.slice(0, -1);
    const targetParts = fileSiteRootParts().concat(targetPath.split('/').filter(Boolean));

    return relativeHref(currentDirParts, targetParts) + suffix;
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
      link.href = siteHref(target === 'en' ? section.enHref : section.ruHref);
    });

    document.querySelectorAll('.navbar a.nav-link').forEach((link) => {
      const label = link.textContent.trim();
      if (label !== 'RU' && label !== 'EN') return;
      const section = sections.find((item) => item.key === key) || sections[0];
      link.href = siteHref(label === 'RU' ? section.ruHref : section.enHref);
      link.addEventListener('click', () => rememberLanguage(label.toLowerCase()));
    });

    rememberLanguage(activeLanguage);
  }


  function openLinkedDetails() {
    const rawHash = window.location.hash ? window.location.hash.slice(1) : '';
    if (!rawHash) return;

    const target = document.getElementById(decodeURIComponent(rawHash));
    if (!target) return;

    let details = target instanceof HTMLDetailsElement ? target : target.closest('details');
    while (details) {
      details.open = true;
      details = details.parentElement ? details.parentElement.closest('details') : null;
    }
  }


  function updateLandingHighlight() {
    const language = preferredLanguage();

    document.querySelectorAll('[data-language-choice]').forEach((choice) => {
      choice.classList.toggle('is-preferred', choice.getAttribute('data-language-choice') === language);
      choice.addEventListener('click', () => rememberLanguage(choice.getAttribute('data-language-choice')));
    });
  }

  updateNavbar();
  updateLandingHighlight();
  openLinkedDetails();
  window.addEventListener('hashchange', openLinkedDetails);
})();
