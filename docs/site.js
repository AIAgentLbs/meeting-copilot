document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    const node = document.getElementById(button.dataset.copy);
    const old = button.textContent;
    const ru = document.documentElement.lang === 'ru';
    const status = button.closest('.install').querySelector('.copy-status');
    const terminal = button.dataset.copy === 'windows-install-command' ? 'PowerShell' : 'Terminal';
    button.disabled = true;
    try {
      await navigator.clipboard.writeText(node.textContent.trim());
      button.textContent = ru ? 'Скопировано' : 'Copied';
      status.textContent = ru ? `Команда скопирована. Вставьте ее в ${terminal}.` : `Command copied. Paste it into ${terminal}.`;
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
