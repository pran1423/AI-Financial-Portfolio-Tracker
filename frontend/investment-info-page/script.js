document.getElementById('yesBtn').addEventListener('click', function() {
    document.getElementById('additionalOptions').classList.remove('hidden');
});

document.getElementById('noBtn').addEventListener('click', function() {
    document.getElementById('additionalOptions').classList.add('hidden');
});