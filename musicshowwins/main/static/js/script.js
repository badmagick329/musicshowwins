let songsRadio;

function main() {
  songsRadio = document.querySelector("#list_type > input[type=radio]:nth-child(1)");
  mainPage();
}

function mainPage() {
  if (!songsRadio) {
    return
  }
  songsRadio.checked = true;
}

document.addEventListener("DOMContentLoaded", main);
