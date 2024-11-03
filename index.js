// import Plotly from 'plotly-dist-min';

// if you change the version, you need to change the reverse proxy conf too in etc/nginx.conf
const backend = '/v1';
// depending on what the proxy support
const https_headers = { headers: { 'Accept-Encoding': 'bz2, gzip, deflate', 'Content-Type': 'application/json' } };

const hide = (elem) => {
    if (elem) {
        elem.hidden = true;
    } else {
        console.error('Trying to hide an empty element');
    }
};

const show = (elem) => {
    if (elem) {
        elem.hidden = false;
    } else {
        console.error('Trying to show an empty element');
    }
};

// structure of the index.html
// topbar
// select
//    +----- a file
//    +----- for a speaker
//    +----- for a headset
// adapt
//    +----- generic peq
//    +----- parametricEQ
//    +----- Rme
//    +----- Roon
// convert
//    +----- to format
//                  +--- APO
//                       +----- download
//                  +--- AUPreset
//                       +----- download
//                  +--- RmeTotalMixChannelEQ
//                       +----- download
//                  +--- RmeTotalMixRoomEQ
//                       +----- download

const stepSelect = document.querySelector('#stepSelect');

const formUpload = stepSelect.querySelector('#uploadEQ');
const formUploadInput = formUpload.querySelector('input[type=file]');
const formUploadFilename = stepSelect.querySelector('#file-name');

const plots = document.querySelector('#plots');

const selectSpeakers = document.querySelector('#selectSpeakers');
const selectSpeakerEQ = document.querySelector('#selectSpeakerEQ');

const stepConvert = document.querySelector('#stepConvert');
const formConvert = stepConvert.querySelector('#convertEQ');
const formConvertSelect = formConvert.querySelector('#selectFormat');
const formConvertSubmit = formConvert.querySelector('#submitButton');

// ----------------------------------------------------------------------
// state abstraction
// ----------------------------------------------------------------------
class EQState {
    constructor(hash, name) {
        if (hash.length === 128) {
            this._hash = hash;
            this._name = name;
        } else {
            console.log('Length of hash is ' + hash.lenght);
        }
    }

    set hash(h) {
        if (h.length === 128) {
            this._hash = h;
        } else {
            console.log('Len of hash is not correct ' + h.length);
        }
    }
    get hash() {
        return this._hash;
    }

    set name(n) {
        this._name = n;
    }
    get name() {
        return this._name;
    }

    valid() {
        return true; // this._hash.length === 128 && this._name.length > 0;
    }
}

class State {
    constructor() {
        this._items = [];
    }

    length() {
        return this._items.length;
    }

    setItems(item) {
        this._items.push(item);
    }

    getItems() {
        return this._items;
    }

    reset() {
        this._items = [];
    }

    hash(k) {
        return this._items[k].hash;
    }

    name(k) {
        return this._items[k].name;
    }
}

const state = new State();

// ----------------------------------------------------------------------
// helper functions
// ----------------------------------------------------------------------

function importIncludes() {
    // helper for including html fragments (menu, symbols)
    const components = document.querySelectorAll('.includes');
    const loadComponent = async (c) => {
        const { name, ext } = c.dataset;
        const response = await fetch(`${name}.${ext}`);
        const html = await response.text();
        c.innerHTML = html;
    };
    [...components].forEach(loadComponent);
}

function assignDiv(selector, dataList, defText, selected) {
    // populate form inputs from a list
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

function toggleTab(panel, tabId, blockId) {
    // make tabId active and not the others
    const tabs = panel.querySelectorAll('.panel-tabs a');
    tabs.forEach((tab) => {
        if (tab.id === tabId) {
            tab.classList.add('is-active');
        } else {
            if (tab.classList.contains('is-active')) {
                tab.classList.remove('is-active');
            }
        }
    });
    // show blockId and hide others
    const blocks = panel.querySelectorAll('div .panel-block');
    blocks.forEach((block) => {
        if (block.id === blockId) {
            block.style.display = 'block';
            show(block);
        } else {
            block.style.display = 'none';
            hide(block);
        }
    });
}

function tabsAddEvents(panel) {
    // add click event to each tabs of the panel
    if (panel) {
        const tabs = panel.querySelectorAll('.panel-tabs a');
        tabs.forEach((tab) => {
            tab.onclick = () => {
                toggleTab(panel, tab.id, tab.dataset.target);
            };
        });
        // call the first one by default
        if (tabs.length > 0) {
            toggleTab(panel, tabs[0].id, tabs[0].dataset.target);
        }
    }
}

// ----------------------------------------------------------------------
// backend calls
// ----------------------------------------------------------------------

async function uploadFiles(form) {
    const url = backend + '/eq/upload';

    const formData = new FormData();
    for (const file of form.files) {
        formData.append('files', file);
    }
    const fetchOptions = {
        method: 'post',
        mode: 'cors',
        body: formData,
    };

    const response = await fetch(url, fetchOptions);
    const text = await response.json();
    return text;
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
            const eq = new EQState(hash, speakerName + ' - ' + selectedSpeakerEQ);
            state.reset();
            state.setItems(eq);
            plotState();
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

// ----------------------------------------------------------------------
// poor man xml encoder
// ----------------------------------------------------------------------
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

function text2code(text) {
    const space4 = '&nbsp;&nbsp;&nbsp;&nbsp';
    let code = '';
    let indent = 0;
    const lines = text.split('\n');
    lines.forEach((line) => {
        let space = '';
        const pos = line.indexOf('<');
        if (pos !== -1 && pos + 1 < line.length && line[pos + 1] !== '/') {
            indent += 1;
        }
        if (line.indexOf('</') !== -1 || line.indexOf('/>') !== -1) {
            indent = Math.max(0, indent - 1);
        }
        for (let i = 0; i < indent; i++) {
            space += space4;
        }
        if (line.indexOf('<?xml') === 0 || line.indexOf('<!DOCTYPE') === 0 || line.indexOf('<Preset>') === 0) {
            space = '';
            indent = 0;
        }
        const encoded = xml2html(line);
        code += space + encoded + '<br/>';
    });
    return code;
}

// ----------------------------------------------------------------------
// display each format
// ----------------------------------------------------------------------

class Format {
    // each format need to support display (the converted format) and download

    async display(fileName, div, hash) {}

    async download(fileName, hash) {}
}

function downloadViaData(fileName, returnType, data) {
    let element = document.createElement('a');
    element.setAttribute('href', 'data:text/' + returnType + ';charset=utf-8, ' + encodeURIComponent(data));
    element.setAttribute('download', fileName);
    console.log('download: ' + fileName);
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

class APO extends Format {
    async display(fileName, div, hash) {
        const url = backend + '/eq/target/apo';
        const response = await fetch(url + '?hash=' + hash, https_headers);
        const data = await response.json();
        div.querySelector('code').innerHTML = text2code(data);
        div.querySelector('#download').onclick = () => {
            this.download(fileName, hash);
        };
        show(div);
    }

    async download(fileName, hash) {
        const url = backend + '/eq/target/apo';
        const response = await fetch(url + '?hash=' + hash, https_headers);
        const data = await response.json();
        downloadViaData(fileName, 'plain', data);
    }
}

const apo = new APO();

class AUPreset extends Format {
    async display(fileName, div, hash) {
        const url = backend + '/eq/target/aupreset';
        const response = await fetch(url + '?hash=' + hash, https_headers);
        const data = await response.json();
        div.querySelector('code').innerHTML = text2code(data[1]);
        div.querySelector('#download').onclick = () => {
            this.download(fileName, hash);
        };
        show(div);
    }

    async download(fileName, hash) {
        const url = backend + '/eq/target/aupreset';
        const response = await fetch(url + '?hash=' + hash, https_headers);
        const data = await response.json();

        let aupresetName = fileName;
        if (aupresetName.length > 4) {
            aupresetName = fileName.slice(0, -4) + '.aupreset';
        }
        downloadViaData(aupresetName, 'xml', data);
    }
}

const aupreset = new AUPreset();

class RMETotalMixChannel extends Format {
    async display(fileName, div, hash) {
        const url = backend + '/eq/target/rme_totalmix_channel';
        const response = await fetch(url + '?hash=' + hash, https_headers);
        const data = await response.json();
        div.querySelector('code').innerHTML = text2code(data);
        div.querySelector('#download').onclick = () => {
            this.download(fileName, hash);
        };
        show(div);
    }

    async download(fileName, hash) {
        const url = backend + '/eq/target/rme_totalmix_channel';
        const response = await fetch(url + '?hash=' + hash, https_headers);
        const data = await response.json();

        let tmeqName = fileName;
        if (tmeqName.length > 4) {
            tmeqName = fileName.slice(0, -4) + '.tmeq';
        }
        downloadViaData(tmeqName, 'xml', data);
    }
}

const rmetotalmixchannel = new RMETotalMixChannel();

class RmeTotalMixRoom extends Format {
    async display(fileName, div, hash0, hash1) {
        const url = backend + '/eq/target/rme_totalmix_room';
        const response = await fetch(url + '?hash_left=' + hash0 + '&hash_right=' + hash1, https_headers);
        const data = await response.json();
        div.querySelector('code').innerHTML = text2code(data);
        div.querySelector('#download').onclick = () => {
            this.download(fileName, hash0, hash1);
        };
        show(div);
    }

    async download(fileName, hash0, hash1) {
        const url = backend + '/eq/target/rme_totalmix_channel';
        const response = await fetch(url + '?hash_left=' + hash0 + '&hash_right=' + hash1, https_headers);
        const data = await response.json();

        let tmreqName = fileName;
        if (tmreqName.length > 4) {
            tmreqName = fileName.slice(0, -4) + '.tmreq';
        }
        downloadViaData(tmreqName, 'xml', data);
    }
}

const rmetotalmixroom = new RmeTotalMixRoom();

// ----------------------------------------------------------------------
// plot EQ
// ----------------------------------------------------------------------

function screen2wh() {
    const ww = window.innerWidth;
    const wh = window.innerHeight;
    const margin = 0;
    let w = ww;
    let h = wh;
    w = Math.min(Math.max(300, ww - margin), 800);
    h = w / 2;
    return [w, h];
}

function peq2graph(freq, spl) {
    const [w, h] = screen2wh();
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
            l: 30,
            r: 120,
            t: 10,
            b: 60,
        },
    };
    const config = {
        responsive: true,
        displayModeBar: false,
    };
    return [data, layout, config];
}

function iir2graph(freq, spls) {
    const [w, h] = screen2wh();
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
            l: 30,
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

// ----------------------------------------------------------------------
// display the plots for each EQ in the state
// ----------------------------------------------------------------------

async function plotState() {
    let contentTabs = '';
    let contentBlocks = '';
    for (let k = 0; k < state.length(); k++) {
        let classActive = '';
        let active = '';
        let hidden = 'hidden';
        if (k == 0) {
            active = ' is-active';
            classActive = ' class="is-active"';
            hidden = '';
        }
        contentTabs += `
<a ${classActive} id="name${k}" data-target="plot${k}">${state.name(k)}</a>
`;
        contentBlocks += `
<div class="panel-block ${active}" id="plot${k}" ${hidden}>
  <div class="columns is-desktop">
    <div class="column is-half" id="plotIIR"></div>
    <div class="column is-half" id="plotPEQ"></div>
  </div>
</div>
`;
    }
    const contentPlots = `
<nav class="panel is-info">
<p class="panel-heading">Plots</p>
<p class="panel-tabs">
${contentTabs}
</p>
${contentBlocks}
</nav>
`;
    show(plots);
    plots.innerHTML = contentPlots;
    for (let k = 0; k < state.length(); k++) {
        const plot = plots.querySelector('#plot' + k);
        const plotPEQ = plot.querySelector('#plotPEQ');
        const plotIIR = plot.querySelector('#plotIIR');
        const status1 = await plotlyPEQ(plotPEQ, state.hash(k));
        const status2 = await plotlyIIR(plotIIR, state.hash(k));
        if (!status1) {
            console.log('Plotting PEQ failed for hash=' + state.hash(k));
        }
        if (!status2) {
            console.log('Plotting IIR failed for hash=' + state.hash(k));
        }
    }
    tabsAddEvents(plots);
    show(stepConvert);
}

// ----------------------------------------------------------------------
// display the eq in each format for each EQ in the state
// ----------------------------------------------------------------------

async function convertState(method) {
    let contentTabs = '';

    for (let k = 0; k < state.length(); k++) {
        let classActive = '';
        if (k == 0) {
            classActive = ' class="is-active"';
        }
        contentTabs += `<a${classActive} id="name${k}" data-target="convert${k}">${state.name(k)}</a>`;
    }

    // show
    show(stepConvert);
    // set new tabs
    stepConvert.querySelector('#tabs').innerHTML = contentTabs;
    // remove old blocks if we have some
    const panel = stepConvert.querySelector('#convertEQ');
    const oldBlocks = panel.querySelectorAll('div.panel-block');
    oldBlocks.forEach((node) => {
        panel.removeChild(node);
    });
    // add new blocks
    for (let k = 0; k < state.length(); k++) {
        const fragment = new DocumentFragment();
        const div = document.createElement('div');
        div.setAttribute('class', 'panel-block');
        div.setAttribute('id', 'convert' + k);
        div.innerHTML = `
    <div id="APO" hidden>
      <code class="is-size-7">
      </code>
      <div class="control">
        <button class="button is-link" id="download">Download</button>
      </div>
    </div>
    <div id="AUPreset" hidden>
      <code class="is-size-7">
      </code>
      <div class="control">
        <button class="button is-link" id="download">Download</button>
      </div>
    </div>
    <div id="Rme-TotalMix-Channel" hidden>
      <code class="is-size-7">
      </code>
      <div class="control">
        <div class="button is-link" id="download">Download</div>
      </div>
    </div>
    <div id="Rme-TotalMix-Room" hidden>
      <code class="is-size-7">
      </code>
      <div class="control">
        <button class="button is-link" id="download">Download</button>
      </div>
    </div>
`;
        fragment.appendChild(div);
        panel.appendChild(fragment);
    }
    for (let k = 0; k < state.length(); k++) {
        const hash = state.hash(k);
        const name = state.name(k);
        const convert = panel.querySelector('#convert' + k);
        const eApo = convert.querySelector('#APO');
        const eAUPreset = convert.querySelector('#AUPreset');
        const eRmeTotalMixChannel = convert.querySelector('#Rme-TotalMix-Channel');
        const eRmeTotalMixRoom = convert.querySelector('#Rme-TotalMix-Room');
        // need some polymorphism
        if (method == 'apo') {
            apo.display(name, eApo, hash);
        } else if (method == 'aupreset') {
            aupreset.display(name, eAUPreset, hash);
        } else if (method == 'rmetmeq') {
            rmetotalmixchannel.display(name, eRmeTotalMixChannel, hash);
        } else if (method == 'rmetmreq') {
            // would be better with another select to get the 2 eqs among the list
            let k2 = 0;
            if (k < state.length() - 1) {
                k2 = k + 1;
            }
            const hash2 = state.hash(k2);
            rmetotalmixroom.display('roomeq.txt', eRmeTotalMixRoom, hash, hash2);
        }
    }
    tabsAddEvents(panel);
}

// ----------------------------------------------------------------------
// onload
// ----------------------------------------------------------------------

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
        const responses = await uploadFiles(formUploadInput);
        let error = false;
        state.reset();
        let contentMsg = '<ol>';
        for (const k in responses) {
            const response = responses[k];
            if (response.status === 'ok') {
                const eq = new EQState(response['hash'], response['name']);
                if (eq.valid()) {
                    state.setItems(eq);
                    contentMsg += '<li> ok:&nbsp;' + eq.name + '</li>';
                } else {
                    contentMsg += '<li> ko: &nbsp;' + eq.name + ' (' + response.message + ')</li>';
                    error = true;
                }
            }
        }
        contentMsg += '</ol>';
        formUploadFilename.innerHTML = contentMsg;
        if (error) {
            hide(plots);
            hide(stepConvert);
        } else {
            await plotState();
            show(stepConvert);
        }
    };

    formConvertSubmit.onclick = async () => {
        await convertState(formConvertSelect.value);
    };

    document.querySelectorAll('.panel').forEach((panel) => {
        tabsAddEvents(panel);
    });
};
