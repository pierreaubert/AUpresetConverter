const hide = (elem) => {
  if (elem?.classList) {
    elem.classList.add("hidden");
  }
};

const show = (elem) => {
  if (elem?.classList) {
    elem.classList.remove("hidden");
  }
};

function uploadFiles(form) {
  const url = "http://0.0.0.0:8000/v0/eq/upload";
  const formData = new FormData();
  for (const file of form.files) {
    formData.append("file", file);
  }
  const fetchOptions = {
    method: "post",
    mode: "cors",
    body: formData,
  };

  const fetchPromise = fetch(url, fetchOptions);

  return fetchPromise
    .then((response) => response.json())
    .then((data) => {
      return data.hash;
    })
    .catch((error) => {
      console.log(error);
      return "error";
    });
}

function displayEqAPO(hash) {
  const url = "http://0.0.0.0:8000/v0/eq/apo";
  const fetchPromise = fetch(url + "?hash=" + hash);

  fetchPromise
    .then((response) => response.json())
    .then((data) => {
      const eq = document.querySelector("#displayeqapo ul");
      if (eq) {
        while (eq.firstChild) {
          eq.removeChild(eq.firstChild);
        }
        const lines = data.split("\n");
        const fragment = new DocumentFragment();
        lines.forEach((line) => {
          const li = document.createElement("li");
          li.textContent = line;
          fragment.appendChild(li);
        });
        eq.appendChild(fragment);
      }
    })
    .catch((error) => console.log(error));
}

function displayEqAUPreset(hash) {
  const url = "http://0.0.0.0:8000/v0/eq/aupreset";
  const fetchPromise = fetch(url + "?hash=" + hash);

  fetchPromise
    .then((response) => response.json())
    .then((data) => {
      const eq = document.querySelector("#displayeqaupreset ul");
      if (eq && data.length >= 1) {
        while (eq.firstChild) {
          eq.removeChild(eq.firstChild);
        }
        const lines = data[1].split("\n");
        const fragment = new DocumentFragment();
        lines.forEach((line) => {
          const li = document.createElement("li");
          li.textContent = line;
          fragment.appendChild(li);
        });
        eq.appendChild(fragment);
      }
    })
    .catch((error) => console.log(error));
}

window.onload = () => {
  const results = document.querySelector("#displayeq");
  hide(results);
  const form = document.querySelector("#upload-eq input[type=file]");
  form.onchange = () => {
    if (form.files.length > 0) {
      const fileName = document.querySelector("#upload-eq .file-name");
      if (fileName) {
        fileName.textContent = form.files[0].name;
      }
    }
    uploadFiles(form).then((hash) => {
      if (hash !== undefined && hash !== "error") {
        displayEqAPO(hash);
        displayEqAUPreset(hash);
      }
      show(results);
    });
  };
};
