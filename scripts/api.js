/* Material emits document$ after each instant navigation as well as on load. */
function initializeApiParameters() {
  document.querySelectorAll('.api-parameters').forEach((section) => {
    const search = section.querySelector('.api-parameter-search');
    if (!search || search.dataset.ready) return;
    search.dataset.ready = 'true';
    search.hidden = false;

    const input = search.querySelector('input');
    const status = section.querySelector('.api-filter-status');
    const parameters = Array.from(section.querySelectorAll('.api-parameter'));
    const searchable = parameters.map((parameter) => parameter.textContent.toLowerCase());

    input.addEventListener('input', () => {
      const query = input.value.trim().toLowerCase();
      let visible = 0;
      parameters.forEach((parameter, index) => {
        parameter.hidden = !searchable[index].includes(query);
        if (!parameter.hidden) visible += 1;
      });
      status.hidden = !query;
      status.textContent = visible
        ? `${visible} of ${parameters.length} parameters`
        : 'No matching parameters. Try another name, type or keyword.';
    });

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        input.value = '';
        input.dispatchEvent(new Event('input'));
      }
    });
  });
}

if (typeof document$ !== 'undefined') {
  document$.subscribe(initializeApiParameters);
} else if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApiParameters);
} else {
  initializeApiParameters();
}
