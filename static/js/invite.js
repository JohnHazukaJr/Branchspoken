// Invites (family.html)
// "Copy link" and "Copy message" copy the field named in their data-copy.

document.querySelectorAll('[data-copy]').forEach((button) => {
  const field = document.getElementById(button.dataset.copy);
  const label = button.textContent;

  button.addEventListener('click', async () => {
    let text = field.value;
    if (field.id === 'invite-url') text = 'https://' + text;

    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      // older browsers: select the text so it can be copied by hand
      field.select();
      button.textContent = 'Press Ctrl+C to copy';
      return;
    }

    button.textContent = 'Copied!';
    setTimeout(() => {
      button.textContent = label;
    }, 2000);
  });
});
