// Story reader (story.html)
// Follows along in the transcript while the recording plays,
// and jumps the recording to any paragraph that gets clicked.

const audio = document.querySelector('.player audio');
const transcriptSection = document.querySelector('.transcript');
const paragraphs = Array.from(transcriptSection.querySelectorAll('p'));

// longer paragraphs take longer to say, so split the time by length
const lengths = paragraphs.map((p) => p.textContent.trim().length);
const totalLength = lengths.reduce((sum, length) => sum + length, 0);
const starts = [];
lengths.reduce((position, length) => {
  starts.push(position);
  return position + length;
}, 0);

function highlightCurrent() {
  if (!audio.duration) return;

  const position = (audio.currentTime / audio.duration) * totalLength;

  paragraphs.forEach((p, i) => {
    const start = starts[i];
    const end = start + lengths[i];
    p.classList.toggle('is-current', position >= start && position < end);
    p.classList.toggle('is-upcoming', position < start);
  });
}

audio.addEventListener('play', () => transcriptSection.classList.add('is-playing'));
audio.addEventListener('timeupdate', highlightCurrent);
audio.addEventListener('ended', () => {
  transcriptSection.classList.remove('is-playing');
  paragraphs.forEach((p) => p.classList.remove('is-current', 'is-upcoming'));
});

paragraphs.forEach((p, i) => {
  p.addEventListener('click', (event) => {
    // links to records still open the record
    if (event.target.closest('a') || !audio.duration) return;
    audio.currentTime = (starts[i] / totalLength) * audio.duration;
    audio.play();
  });
});
