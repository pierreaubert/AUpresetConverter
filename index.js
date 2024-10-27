const hide = (elem) => {
    if (elem) {
	elem.hidden = true;
    }
};

const show = (elem) => {
    if (elem) {
	elem.hidden = false;
    }
};

const https_headers = { headers: { 'Accept-Encoding': 'bz2, gzip, deflate', 'Content-Type': 'application/json' }};

async function uploadFiles(form) {
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

    const response = await fetch(url, fetchOptions);
    console.log('ok=' + response.ok + ' status=' + response.status);
    const text = await response.json();
    console.log(text.message);
    return text;
}

async function displayEqAPO(hash) {
    const eq = document.querySelector("#displayEQAPO ul");
    const url = "http://0.0.0.0:8000/v0/eq/target/apo";
    if (hash === null || hash.length !== 128 ) {
	return;
    }
    const response = await fetch(url + "?hash=" + hash, https_headers);

    const data = await response.json();
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
}

async function displayEqAUPreset(hash) {
    const url = "http://0.0.0.0:8000/v0/eq/target/aupreset";
    if (hash === null || hash.length !== 128 ) {
	return;
    }
    const response = await fetch(url + "?hash=" + hash, https_headers);

    const data = await response.json();
    const eq = document.querySelector("#displayEQAUpreset ul");
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
}

function peq2graph(freq, spl) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const data = [{
	x: freq,
	y: spl,
	type: 'scatter'
    }]
    const layout = {
	width: w-40,
	height: w/2,
	xaxis: {
	    title: {
		text: 'Freq (Hz)'
	    },
	    type: "log",
	    range: [Math.log10(20), Math.log10(20000)],
	    showline: true,
	    dtick:"D1"
	},
	yaxis: {
	    title: {
		text: 'SPL (dB)'
	    }
	},
	margin: {
	    l: 40,
	    r: 120,
	    t: 10,
	    b: 60
	}
    }
    const config = {
	responsive: false,
	displayModeBar: false
    }
    return [data, layout, config];
}

function iir2graph(freq, spls) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const data = []
    spls.forEach( (value) => {
	data.push({
	    x: freqs,
	    y: value,
	    type: 'scatter'
	});
    });
    const layout = {
	width: w-40,
	height: w/2,
	xaxis: {
	    title: {
		text: 'Freq (Hz)'
	    },
	    type: "log",
	    range: [Math.log10(20), Math.log10(20000)],
	    showline: true,
	    dtick:"D1"
	},
	yaxis: {
	    title: {
		text: 'SPL (dB)'
	    }
	},
	margin: {
	    l: 40,
	    r: 120,
	    t: 10,
	    b: 60
	}
    }
    const config = {
	responsive: false,
	displayModeBar: false
    }
    return [data, layout, config];
}

async function plotlyPEQ(div, hash) {
    const url = "http://0.0.0.0:8000/v0/eq/graph_spl";
    if (hash === null || hash.length !== 128 ) {
	return;
    }
    const response = await fetch(url + "?hash=" + hash, https_headers);
    const data = await response.json();
    const specs = peq2graph(data.freq, data.spl);
    Plotly.newPlot(div, specs[0], specs[1], specs[2]);
    return true;
}

async function plotlyIIR(div, hash) {
    const url = "http://0.0.0.0:8000/v0/eq/graph_spl_iir";
    if (hash === null || hash.length !== 128 ) {
	return;
    }
    const response = await fetch(url + "?hash=" + hash, https_headers);
    const data = await response.json();
    const specs = iir2graph(data.freq, data.spl);
    Plotly.newPlot(div, specs[0], specs[1], specs[2]);
    return true;
}

window.onload = () => {

    if (window.trustedTypes && window.trustedTypes.createPolicy && !window.trustedTypes.defaultPolicy) {
	window.trustedTypes.createPolicy('default', {
            createHTML: string => string
	});
    }

    const stepSelect = document.querySelector('#stepSelect');
    const stepConvert = document.querySelector('#stepConvert');

    const formUpload = stepSelect.querySelector("#uploadEQ");
    const formUploadInput = formUpload.querySelector("input[type=file]");
    const formUploadFilename = formUpload.querySelector(".file-name");
    const plots = stepSelect.querySelector("#plots");
    const plotPEQ = plots.querySelector("#plotPEQ");
    const plotIIR = plots.querySelector("#plotIIR");

    const formConvert = stepConvert.querySelector("#convertEQ");
    const formConvertHash = formConvert.querySelector("#hash");
    const formConvertSelect = formConvert.querySelector("#selectFormat");
    const formConvertSubmit = formConvert.querySelector("#submitButton");
    const results = stepConvert.querySelector("#displayEQ");

    formUploadInput.onchange = async () => {
	const response = await uploadFiles(formUploadInput);
	if (response.hash !== null) {
	    formConvertHash.value = response.hash;
	    if (formUploadInput.files.length > 0) {
		formUploadFilename.textContent = '> ' + formUploadInput.files[0].name;
	    }
	    const status1 = await plotlyPEQ(plotPEQ, response.hash);
	    const status2 = await plotlyIIR(plotIIR, response.hash);
	    if (status1 && status2) {
		show(plots);
	    }
	    show(stepConvert);
	} else {
	    formUploadFilename.textContent = response.message;
	    hide(plots);
	    hide(stepConvert);
	}
    }

    formConvertSubmit.onclick = async () => {
	const hash = formConvertHash.value;
	if (hash !== "" ) {
	    displayEqAPO(hash);
	    displayEqAUPreset(hash);
	    show(results);
	}
    }
}
