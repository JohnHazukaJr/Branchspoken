// Family tree (tree.html)
// Switches to another family tree as soon as one is picked.

const familyPicker = document.querySelector('#family');

// keep the picker in sync with the family in the address bar
const params = new URLSearchParams(window.location.search);
if (params.has('family')) {
  familyPicker.value = params.get('family');
}

familyPicker.addEventListener('change', () => {
  familyPicker.form.submit();
});
