// Guided interview recorder (add-memory.html)
// Records audio from the microphone, keeps a running timer,
// steps through interview questions and transcribes speech
// in browsers that support it.

const form = document.querySelector('.page-record form');
const timer = document.querySelector('.timer');
const recordButton = document.querySelector('.record-button');
const statusMessage = document.querySelector('.record-status');
const audioInput = document.querySelector('#audio');
const durationInput = document.querySelector('#duration');
const transcript = document.querySelector('#transcript');
const storyteller = document.querySelector('#storyteller');
const recordingHeading = document.querySelector('#recording-heading');

const questionCount = document.querySelector('.question .eyebrow');
const questionHeading = document.querySelector('#question-heading');
const questionInput = document.querySelector('input[name="question"]');
const [followUpButton, skipButton] = document.querySelectorAll('.question .button');

// the interview questions come from the server, on the question section
const questions = JSON.parse(document.querySelector('.question').dataset.questions);

const followUps = [
  'Can you tell me more about that?',
  'Who else was there?',
  'What happened next?',
  'How did that feel at the time?'
];

let questionIndex = Number(questionInput.value) - 1;
let followUpIndex = 0;

let mediaRecorder = null;
let chunks = [];
let startedAt = 0;
let timerId = null;
let recognition = null;
let isRecording = false;


// ---------- Who is being recorded ----------

function updateRecordingHeading() {
  const option = storyteller.options[storyteller.selectedIndex];
  const name = option.text.split(',')[0];
  const relation = option.text.split(',')[1] || '';

  if (storyteller.value === 'me') {
    recordingHeading.textContent = 'Recording yourself';
  } else if (relation.includes('grandfather')) {
    recordingHeading.textContent = 'Recording Grandpa ' + name.split(' ')[0];
  } else if (relation.includes('grandmother')) {
    recordingHeading.textContent = 'Recording Grandma ' + name.split(' ')[0];
  } else {
    recordingHeading.textContent = 'Recording ' + name;
  }
}

storyteller.addEventListener('change', updateRecordingHeading);


// ---------- Questions ----------

function showQuestion(text, label) {
  questionHeading.textContent = text;
  questionCount.textContent = label;

  // mark where each new question starts in the transcript
  if (isRecording && transcript.value.trim() !== '') {
    transcript.value = transcript.value.trimEnd() + '\n\n' + text + '\n';
  }
}

skipButton.addEventListener('click', () => {
  questionIndex = (questionIndex + 1) % questions.length;
  followUpIndex = 0;
  questionInput.value = questionIndex + 1;
  showQuestion(questions[questionIndex], `Question ${questionIndex + 1} of ${questions.length}`);
});

followUpButton.addEventListener('click', () => {
  const text = followUps[followUpIndex % followUps.length];
  followUpIndex++;
  showQuestion(text, `Follow-up to question ${questionIndex + 1}`);
});


// ---------- Timer ----------

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}

function startTimer() {
  startedAt = Date.now();
  timer.textContent = '0:00';
  timerId = setInterval(() => {
    timer.textContent = formatTime(Date.now() - startedAt);
  }, 250);
}

function stopTimer() {
  clearInterval(timerId);
}


// ---------- Live transcript ----------

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function startTranscribing() {
  if (!SpeechRecognition) return;

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  let finished = transcript.value;

  recognition.addEventListener('result', (event) => {
    let inProgress = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const words = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finished = (finished.trimEnd() + ' ' + words.trim()).trim();
      } else {
        inProgress += words;
      }
    }

    transcript.value = (finished + ' ' + inProgress).trim();
    transcript.scrollTop = transcript.scrollHeight;
  });

  // the browser stops listening after a long pause, so pick back up
  recognition.addEventListener('end', () => {
    if (isRecording) {
      finished = transcript.value;
      recognition.start();
    }
  });

  recognition.start();
}

function stopTranscribing() {
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
}


// ---------- Recording ----------

function setRecording(on) {
  isRecording = on;
  form.classList.toggle('is-recording', on);
  recordButton.setAttribute('aria-pressed', on);
  recordButton.textContent = on ? 'Stop recording' : 'Start recording';
}

async function startRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    statusMessage.textContent = "This browser can't record. You can upload a recording instead.";
    return;
  }

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    statusMessage.textContent = 'Microphone access was blocked. Allow it in your browser settings to record.';
    return;
  }

  chunks = [];
  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.addEventListener('dataavailable', (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  });

  mediaRecorder.addEventListener('stop', () => {
    stream.getTracks().forEach((track) => track.stop());

    // put the recording in the file field so it uploads with the form
    const type = mediaRecorder.mimeType || 'audio/webm';
    const extension = type.includes('ogg') ? 'ogg' : type.includes('mp4') ? 'm4a' : 'webm';
    const file = new File(chunks, `recording.${extension}`, { type });
    const files = new DataTransfer();
    files.items.add(file);
    audioInput.files = files.files;

    statusMessage.textContent = `Saved ${timer.textContent} of audio. It will upload with the story.`;
  });

  mediaRecorder.start();
  setRecording(true);
  startTimer();
  startTranscribing();

  statusMessage.textContent = SpeechRecognition
    ? 'Recording. Tap to stop.'
    : "Recording. Tap to stop. This browser can't transcribe, so type anything you want to keep.";
}

function stopRecording() {
  // tell the server how long the recording is, in seconds
  durationInput.value = Math.round((Date.now() - startedAt) / 1000);
  setRecording(false);
  stopTimer();
  stopTranscribing();
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}

recordButton.addEventListener('click', () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
});

// finish the recording before the story is saved
form.addEventListener('submit', (event) => {
  if (isRecording) {
    event.preventDefault();
    stopRecording();
    mediaRecorder.addEventListener('stop', () => form.requestSubmit(), { once: true });
  }
});
