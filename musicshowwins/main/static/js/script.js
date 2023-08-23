function main() {
  let songsRadio = document.querySelector("#list_type > input[type=radio]:nth-child(1)");
  let dropDownDefault = document.querySelector("#list_filters > select > option:nth-child(1)");
  if (songsRadio) {
    songsRadio.checked = true;
  }
  if (dropDownDefault) {
    dropDownDefault.selected = true;
  }
}

document.addEventListener("DOMContentLoaded", main);
