// https://codepen.io/Garbee/pen/EPoaMj

(function() {
    'use strict';
    var closeDialogButton = document.querySelector('#close-dialog-button');
    var dialog = document.querySelector('#dialog');
    if (!dialog.showModal) {
        dialogPolyfill.registerDialog(dialog);
    }
    dialog.showModal();
    dialog.querySelector('button:not([disabled])')
        .addEventListener('click', function() {
            dialog.close();
        });
}());

function downloadCSSFile (filename) {
    if (filename.length === 0) {
        alert('No file to download!');
        return;
    }

    // https://stackoverflow.com/questions/1066452/easiest-way-to-open-a-download-window-without-navigating-away-from-the-page
    var a = document.createElement('A');
    a.href = filename;
    a.download = filename.substr(filename.lastIndexOf('/') + 1);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

}