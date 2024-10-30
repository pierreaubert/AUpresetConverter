// import Plotly from 'plotly-dist-min';

const backend = 'https://eqconverter.spinorama.org/v1';

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

const https_headers = { headers: { 'Accept-Encoding': 'bz2, gzip, deflate', 'Content-Type': 'application/json' } };

// structure of the index.html
// topbar
// select
//    +----- a file
//    +----- for a speaker
//    +----- for a headset
// adapt
//    +----- generic peq
//    +----- parametricEQ
//    +----- RME
//    +----- Roon
// convert
//    +----- to format
//                  +--- APO
//                  +--- AUPreset
//    +----- download

const topBar = document.querySelector('#topBar');
const navBar = document.querySelector('#navBar');

const stepSelect = document.querySelector('#stepSelect');

const formUpload = stepSelect.querySelector('#uploadEQ');
const formUploadInput = formUpload.querySelector('input[type=file]');
const formUploadFilename = formUpload.querySelector('.file-name');

const plots = stepSelect.querySelector('#plots');
const plotPEQ = plots.querySelector('#plotPEQ');
const plotIIR = plots.querySelector('#plotIIR');

const selectSpeakers = document.querySelector('#selectSpeakers');
const selectSpeakerEQ = document.querySelector('#selectSpeakerEQ');

const stepConvert = document.querySelector('#stepConvert');
const formConvert = stepConvert.querySelector('#convertEQ');
const formConvertHash = formConvert.querySelector('#hash');
const formConvertSelect = formConvert.querySelector('#selectFormat');
const formConvertSubmit = formConvert.querySelector('#submitButton');

const resultsEQ = stepConvert.querySelector('#displayEQ');
const resultsEQAPO = resultsEQ.querySelector('#displayEQAPO');
const resultsEQAUPreset = resultsEQ.querySelector('#displayEQAUPreset');

const formDownloadAPO = stepConvert.querySelector('#downloadAPO');
const formDownloadAUPreset = stepConvert.querySelector('#downloadAUPreset');

function importIncludes() {
    const components = document.querySelectorAll('.includes')
    const loadComponent = async c => {
        const { name, ext } = c.dataset
        const response = await fetch(`${name}.${ext}`)
        const html = await response.text()
        c.innerHTML = html
    }
    [...components].forEach(loadComponent);
}

async function uploadFiles(form) {
    const url = backend + '/eq/upload';
    const formData = new FormData();
    for (const file of form.files) {
        formData.append('file', file);
    }
    const fetchOptions = {
        method: 'post',
        mode: 'cors',
        body: formData,
    };

    const response = await fetch(url, fetchOptions);
    console.log('ok=' + response.ok + ' status=' + response.status);
    const text = await response.json();
    console.log(text.message);
    return text;
}

function assignDiv(selector, dataList, defText, selected) {
    while (selector.firstChild) {
        selector.firstChild.remove();
    }
    const defOption = document.createElement('option');
    defOption.value = '';
    defOption.text = defText;
    selector.appendChild(defOption);
    for (const element of dataList) {
        const currentOption = document.createElement('option');
        currentOption.value = element;
        currentOption.text = element.replace('Vendors-', '').replace('vendor-pattern-', 'Pattern ');
        if (element === selected) {
            currentOption.selected = true;
        }
        if (dataList.length === 1) {
            currentOption.disabled = true;
        }
        selector.appendChild(currentOption);
    }
}

async function setSpeakerEQ(speakerName) {
    const url = backend + '/speaker/' + speakerName + '/eqdata';
    const response = await fetch(url, https_headers);

    const data = await response.json();
    const labels = data.map((v) => v['name']);

    if (selectSpeakerEQ) {
        assignDiv(selectSpeakerEQ, labels, 'Select an EQ ...', '');
        show(selectSpeakerEQ);
    } else {
        hide(selectSpeakerEQ);
    }

    selectSpeakerEQ.onchange = async () => {
        const selectedSpeakerEQ = selectSpeakerEQ.value;
        if (selectedSpeakerEQ !== '') {
            let hash = '';
            // must be a filter function somewhere
            data.forEach((v) => {
                if (v['name'] == selectedSpeakerEQ) {
                    hash = v['hash'];
                }
            });
            formConvertHash.value = hash;
            const status1 = await plotlyPEQ(plotPEQ, hash);
            const status2 = await plotlyIIR(plotIIR, hash);
            if (status1 && status2) {
                show(plots);
            }
            show(stepConvert);
        } else {
            hide(plots);
            hide(stepConvert);
        }
    };
    return true;
}

async function loadFromSpinorama() {
    const url = backend + '/speakers';
    const response = await fetch(url, https_headers);

    const data = await response.json();
    if (selectSpeakers) {
        assignDiv(selectSpeakers, data, 'Select a speaker ...', '');
    }

    selectSpeakers.onchange = async () => {
        const selectedSpeaker = selectSpeakers.value;
        if (selectedSpeaker !== '') {
            setSpeakerEQ(selectedSpeaker);
            hide(plots);
            hide(stepConvert);
        }
    };

    return true;
}

async function displayEqAPO(hash) {
    const eq = document.querySelector('#displayEQAPO p');
    const url = backend + '/eq/target/apo';
    if (hash === null || hash.length !== 128) {
        return;
    }
    const response = await fetch(url + '?hash=' + hash, https_headers);

    const data = await response.json();
    if (eq) {
        const lines = data.split('\n');
        let content = '';
        lines.forEach((line) => {
            content += line + '<br/>';
        });
        eq.innerHTML = content;
    }
}

async function downloadAPO(fileName, hash) {
    const url = backend + '/eq/target/apo';
    if (hash === null || hash.length !== 128) {
        return;
    }
    const response = await fetch(url + '?hash=' + hash, https_headers);

    const data = await response.json();
    let element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8, ' + encodeURIComponent(data));
    element.setAttribute('download', fileName);
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

async function downloadAUPreset(fileName, hash) {
    const url = backend + '/eq/target/aupreset';
    if (hash === null || hash.length !== 128) {
        return;
    }
    const response = await fetch(url + '?hash=' + hash, https_headers);
    const data = await response.json();

    let aupresetName = fileName;
    if (aupresetName.length > 4) {
        aupresetName = fileName.slice(0, -4) + '.aupreset';
    }
    let element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8, ' + encodeURIComponent(data));
    element.setAttribute('download', aupresetName);
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

function xml2html(s) {
    return s.replace(/[<>"'&]/g, function (char) {
        switch (char) {
            case '<':
                return '&lt;';
            case '>':
                return '&gt;';
            case '"':
                return '&quot;';
            case "'":
                return '&apos;';
            case '&':
                return '&amp;';
        }
    });
}

async function displayEqAUPreset(hash) {
    const url = backend + '/eq/target/aupreset';
    if (hash === null || hash.length !== 128) {
        return;
    }
    const response = await fetch(url + '?hash=' + hash, https_headers);

    const data = await response.json();
    const eq = document.querySelector('#displayEQAUPreset p');
    if (eq && data.length >= 1) {
        const lines = data[1].split('\n');
        let content = '';
        lines.forEach((line) => {
            content += xml2html(line) + '<br/>';
        });
        eq.innerHTML = content;
    }
}

function peq2graph(freq, spl) {
    const ww = Math.min(window.innerWidth, 600);
    const wh = window.innerHeight;
    let w = ww - 40;
    let h = ww / 2;
    if (ww < wh) {
        let h = wh - 40;
        let w = wh / 2;
    }
    const data = [
        {
            x: freq,
            y: spl,
            type: 'scatter',
        },
    ];
    const layout = {
        width: w,
        height: h,
        xaxis: {
            title: {
                text: 'Freq (Hz)',
            },
            type: 'log',
            range: [Math.log10(20), Math.log10(20000)],
            showline: true,
            dtick: 'D1',
        },
        yaxis: {
            title: {
                text: 'SPL (dB)',
            },
        },
        margin: {
            l: 40,
            r: 120,
            t: 10,
            b: 60,
        },
    };
    const config = {
        responsive: false,
        displayModeBar: false,
    };
    return [data, layout, config];
}

function iir2graph(freq, spls) {
    const ww = Math.min(window.innerWidth, 600);
    const wh = window.innerHeight;
    let w = ww - 40;
    let h = ww / 2;
    if (ww < wh) {
        let h = wh - 40;
        let w = wh / 2;
    }

    const data = [];
    // spls is a js object without any method ....
    for (let i = 0; i < 32; i++) {
        const value = spls[i];
        if (value === undefined) {
            break;
        }
        data.push({
            x: freq,
            y: value,
            showlegend: false,
            type: 'scatter',
        });
    }
    const layout = {
        width: w,
        height: h,
        xaxis: {
            title: {
                text: 'Freq (Hz)',
            },
            type: 'log',
            range: [Math.log10(20), Math.log10(20000)],
            showline: true,
            dtick: 'D1',
        },
        yaxis: {
            title: {
                text: 'SPL (dB)',
            },
        },
        margin: {
            l: 40,
            r: 120,
            t: 10,
            b: 60,
        },
    };
    const config = {
        responsive: false,
        displayModeBar: false,
    };
    return [data, layout, config];
}

async function plotlyPEQ(div, hash) {
    const url = backend + '/eq/graph_spl';
    if (hash === null || hash.length !== 128) {
        return;
    }
    const response = await fetch(url + '?hash=' + hash, https_headers);
    const data = await response.json();
    const specs = peq2graph(data.freq, data.spl);
    Plotly.newPlot(div, specs[0], specs[1], specs[2]);
    return true;
}

async function plotlyIIR(div, hash) {
    const url = backend + '/eq/graph_spl_details';
    if (hash === null || hash.length !== 128) {
        return;
    }
    const response = await fetch(url + '?hash=' + hash, https_headers);
    const data = await response.json();
    const specs = iir2graph(data.freq, data.spl);
    Plotly.newPlot(div, specs[0], specs[1], specs[2]);
    return true;
}

window.onload = () => {
    if (window.trustedTypes && window.trustedTypes.createPolicy && !window.trustedTypes.defaultPolicy) {
        window.trustedTypes.createPolicy('default', {
            createHTML: (string) => string,
        });
    }

    importIncludes();

    // load initial data
    const statusLoadSpinorama = loadFromSpinorama();
    if (!statusLoadSpinorama) {
        console.log('Load speaker database failed!');
    }

    // Upload
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
    };

    // Convert
    formConvertSubmit.onclick = async () => {
	hide(resultsEQ);
        const hash = formConvertHash.value;
	const method = formConvertSelect.value;
        if (hash !== '' && method !== '') {
            show(resultsEQ);
	    hide(resultsEQAPO);
	    hide(resultsEQAUPreset);
	    if (method === 'APO') {
		displayEqAPO(hash);
		show(resultsEQAPO);
	    } else if (method === 'AUPreset') {
		displayEqAUPreset(hash);
		show(resultsEQAUPreset);
	    }
        }
    };

    // Download
    formDownloadAPO.onclick = async () => {
        const filename = formUploadFilename.textContent.slice(2);
        const hash = formConvertHash.value;
        await downloadAPO(filename, hash);
    };

    formDownloadAUPreset.onclick = async () => {
        const filename = formUploadFilename.textContent.slice(2);
        const hash = formConvertHash.value;
        await downloadAUPreset(filename, hash);
    };
};
