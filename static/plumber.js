async function getData() {
    const now = new Date();
    const startTime = `2020-${(''+(now.getMonth()+1)).padStart(2, '0')}-${(''+now.getDate()).padStart(2, '0')}`;
    const inOneWeek = new Date(now.getTime() + 24*60*60*7*1000);
    const endTime = `2020-${(''+(inOneWeek.getMonth()+1)).padStart(2, '0')}-${(''+inOneWeek.getDate()).padStart(2, '0')}`;
    const response = await fetch(`/device_specific_consumption?start=${startTime}&end=${endTime}`)
    const body = await response.json()
    return body
}

function renderTableRow(columns, isHeader=false) {
    const tr = document.createElement('tr');
    let counter = 0;
    for (const val of columns) {
        const col = document.createElement(isHeader ? 'th' : 'td');
        col.textContent = val;
        tr.appendChild(col);
        counter++;
    }
    return tr;
}

function renderTable(data) {
    const cols = ['Apartment', 'Hydractiva_shower', 'Kitchen_optima_faucet', 'Optima_faucet', 'Washing_machine', 'Dishwasher'];
    const colNameMap = {
        'Apartment': 'Apartment',
        'Hydractiva_shower': 'Shower',
        'Kitchen_optima_faucet': 'Kitchen faucet',
        'Optima_faucet': 'Faucet',
        'Washing_machine': 'Washing mach.',
        'Dishwasher': 'Dishwasher',
    }
    const tbl = document.querySelector('.tenant-table');
    while (tbl.firstChild){ tbl.removeChild(tbl.firstChild); }
    tbl.appendChild(renderTableRow(cols.map((col) => colNameMap[col]), true));
    for (const [apartmentId, devices] of Object.entries(data)) {
        tbl.appendChild(renderTableRow(
            cols.map((colName) => {
                if (colName === 'Apartment') { return apartmentId; }
                const dev = devices[colName];
                if (dev) { return `${Math.round(dev.flow_percentage * 1000) / 10} %`; /* TODO other stats */ }
                return '0 %';
            })
        ));
    }
}

async function init() {
    const data = await getData()
    renderTable(data);
}

init()
