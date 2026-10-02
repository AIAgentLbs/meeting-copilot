document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    const node = document.getElementById(button.dataset.copy);
    const old = button.textContent;
    const ru = document.documentElement.lang === 'ru';
    const status = document.querySelector('.copy-status');
    button.disabled = true;
    try {
      await navigator.clipboard.writeText(node.textContent.trim());
      button.textContent = ru ? 'Скопировано' : 'Copied';
      status.textContent = ru ? 'Команда скопирована. Вставьте её в Terminal.' : 'Command copied. Paste it into Terminal.';
    } catch (_error) {
      const range = document.createRange();
      range.selectNodeContents(node);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = ru ? 'Браузер запретил копирование. Команда выделена — скопируйте её вручную.' : 'Clipboard access was blocked. The command is selected; copy it manually.';
    } finally {
      setTimeout(() => { button.textContent = old; button.disabled = false; }, 1600);
    }
  });
});
