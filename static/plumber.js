async function getData() {
    const response = await fetch('/device_specific_consumption?start=2020-02-02%2009:00:00&end=2020-02-02%2012:00:00')
    const body = await response.json()
    return body
}

function renderTableRow(columns, isHeader=false) {
    const tr = document.createElement('tr');
    for (const val of columns) {
        const col = document.createElement(isHeader ? 'th' : 'td');
        col.textContent = val;
        tr.appendChild(col);
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
                if (dev) { return `${Math.round(dev.flow_percentage * 100)}%`; /* TODO other stats */ }
                return '';
            })
        ));
        console.log({apartmentId, devices});
    }
}

async function init() {
    const data = await getData()
    console.log(data)
    renderTable(data);
}

init()
