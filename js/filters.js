// Filters and search (stories.html, archive.html)
// Filters the list in place instead of reloading the page.
// The filter links still work on their own if this script doesn't load.

const filterLinks = document.querySelectorAll('.filters a');
const items = document.querySelectorAll('.story-list li, .archive-grid li');
const searchForm = document.querySelector('.search');
const searchInput = document.querySelector('.search input[type="search"]');
const showing = document.querySelector('.showing');

const params = new URLSearchParams(window.location.search);
let currentType = params.get('type') || '';
let currentSearch = params.get('q') || '';

// "Voice", "Photo", "Record"... comes from the type tile or the photo label
function typeOf(item) {
  const label = item.querySelector('.type, figcaption');
  return label ? label.textContent.trim().toLowerCase() : '';
}

function typeFromLink(link) {
  return new URL(link.href).searchParams.get('type') || '';
}

let emptyMessage = null;

function showEmptyMessage(show) {
  if (!emptyMessage) {
    emptyMessage = document.createElement('p');
    emptyMessage.className = 'empty-message';
    emptyMessage.textContent = 'Nothing matches yet. Try another search, or add a memory.';
    items[0].parentElement.after(emptyMessage);
  }
  emptyMessage.hidden = !show;
}

function applyFilters() {
  const search = currentSearch.trim().toLowerCase();
  let visible = 0;

  items.forEach((item) => {
    const matchesType = currentType === '' || typeOf(item) === currentType;
    const matchesSearch = search === '' || item.textContent.toLowerCase().includes(search);
    item.hidden = !(matchesType && matchesSearch);
    if (!item.hidden) visible++;
  });

  filterLinks.forEach((link) => {
    if (typeFromLink(link) === currentType) {
      link.setAttribute('aria-current', 'page');
    } else {
      link.removeAttribute('aria-current');
    }
  });

  if (showing) {
    showing.textContent = currentType || search
      ? `${visible} matching ${visible === 1 ? 'story' : 'stories'}`
      : `Showing ${visible} of 32`;
  }

  showEmptyMessage(visible === 0);

  // keep the address bar in step so the page can be shared or refreshed
  const url = new URL(window.location.href);
  url.searchParams.delete('type');
  url.searchParams.delete('q');
  if (currentType) url.searchParams.set('type', currentType);
  if (search) url.searchParams.set('q', currentSearch.trim());
  history.replaceState(null, '', url);
}

filterLinks.forEach((link) => {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    currentType = typeFromLink(link);
    applyFilters();
  });
});

if (searchForm) {
  searchInput.value = currentSearch;

  searchInput.addEventListener('input', () => {
    currentSearch = searchInput.value;
    applyFilters();
  });

  searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    currentSearch = searchInput.value;
    applyFilters();
  });
}

applyFilters();
