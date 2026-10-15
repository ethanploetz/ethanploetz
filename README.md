# Ethan's Hub (private copy)

`index.html` is a password-protected, read-only copy of Ethan's personal hub. Its contents are encrypted (AES-256 via StatiCrypt); nothing in this repository is readable without the password.

`tools/` holds the build script that turns a data export into `index.html`. It strips grades, phone number, team travel logistics, booking confirmation numbers and photos before encrypting.
