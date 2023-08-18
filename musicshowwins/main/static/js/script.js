let artistSearch, songsRadio, artistsRadio, songsLabel, artistsLabel;

function main() {
  artistSearch = document.querySelector("#artist-search");
  songsRadio = document.querySelector("#list-type > input[type=radio]:nth-child(1)");
  artistsRadio = document.querySelector("#list-type > input[type=radio]:nth-child(3)");
  songsLabel = document.querySelector("#list-type > label:nth-child(2)");
  artistsLabel = document.querySelector("#list-type > label:nth-child(4)");
  artistSearch.value = "";
  songsRadio.checked = true;
  artistSearch.addEventListener("keyup", function (e) {
    e.target.value == "" ? undimLabels() : dimLabels();
  });
  songsRadio.addEventListener("click", function (e) {
    artistSearch.value = "";
    undimLabels();
  });
  artistsRadio.addEventListener("click", function (e) {
    artistSearch.value = "";
    undimLabels();
  });
}

function dimLabels() {
  songsLabel.classList.add("opacity-50");
  artistsLabel.classList.add("opacity-50");
  songsLabel.classList.remove("opacity-100");
  artistsLabel.classList.remove("opacity-100");
}

function undimLabels() {
  songsLabel.classList.add("opacity-100");
  artistsLabel.classList.add("opacity-100");
  songsLabel.classList.remove("opacity-50");
  artistsLabel.classList.remove("opacity-50");
}

document.addEventListener("DOMContentLoaded", main);
