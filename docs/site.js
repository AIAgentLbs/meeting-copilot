document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    const node = document.getElementById(button.dataset.copy);
    await navigator.clipboard.writeText(node.textContent.trim());
    const old = button.textContent;
    button.textContent = document.documentElement.lang === 'ru' ? 'Скопировано' : 'Copied';
    setTimeout(() => { button.textContent = old; }, 1600);
  });
});

