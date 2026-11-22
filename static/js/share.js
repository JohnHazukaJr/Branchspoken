// Share a relative's page (relative.html)
// Uses the phone's share sheet when there is one, otherwise copies the link.

const shareLink = document.querySelector('.pill');

shareLink.addEventListener('click', async (event) => {
  event.preventDefault();

  const name = document.querySelector('h1').textContent;
  const page = { title: `${name} | Branch Spoken`, url: window.location.href };

  if (navigator.share) {
    try {
      await navigator.share(page);
    } catch (error) {
      // closing the share sheet counts as an error, nothing to do
    }
    return;
  }

  try {
    await navigator.clipboard.writeText(page.url);
    shareLink.textContent = 'Link copied';
  } catch (error) {
    shareLink.textContent = "Couldn't copy";
  }

  setTimeout(() => {
    shareLink.textContent = 'Share';
  }, 2000);
});
