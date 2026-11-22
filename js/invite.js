// Invite link (family.html)
// Copies the invite link so it can be pasted into a text or email.

const copyButton = document.querySelector('.invite-link button');
const linkField = document.querySelector('#invite-url');

copyButton.addEventListener('click', async () => {
  const link = 'https://' + linkField.value;

  try {
    await navigator.clipboard.writeText(link);
  } catch (error) {
    // older browsers: select the text so it can be copied by hand
    linkField.select();
    copyButton.textContent = 'Press Ctrl+C to copy';
    return;
  }

  copyButton.textContent = 'Copied!';
  setTimeout(() => {
    copyButton.textContent = 'Copy link';
  }, 2000);
});
