const urlParams = new URLSearchParams(window.location.search)
const query = urlParams.get('q')

let h1Prefix = 'Total'
if (query === 'manual') h1Prefix = 'Shower and faucet'
if (query === 'automatic') h1Prefix = 'Appliance'
document.getElementsByTagName('h1')[0].innerText = `${h1Prefix} consumption details 💧`

function instantiateChart(datasets) {
    const ctx = document.getElementById('chart').getContext('2d')
    const dayInMilliseconds = 24 * 60 * 60 * 1000
    const currentDate = new Date(new Date())

    const labels = [...Array(7).keys()]
        .map(x => x - 1)
        .reverse()
        .map(x => new Date(currentDate.getTime() + x * dayInMilliseconds))
        .map(x => x.toLocaleString('en-US', {weekday: 'long'}))

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets
        },
        options: {
            events: [],
            maintainAspectRatio: false,
        }
    })
}

async function getDatasetValues(query) {
    const dayInMilliseconds = 24 * 60 * 60 * 1000
    const currentDate = new Date(new Date().toISOString().slice(0, 10))
    // Set currentDate year to 2020 so we can use our data from 2020
    currentDate.setFullYear(2020)
    
    let dataset = []
    
    for (let i = 0; i >- 7; i--) {
        const start = new Date(currentDate.getTime() + (i - 1) * dayInMilliseconds).toISOString().slice(0, 10)
        const end = new Date(currentDate.getTime() + i * dayInMilliseconds).toISOString().slice(0, 10)
        if (['manual', 'automatic'].includes(query)) {
            const response = await fetch(`/apartment_device_stats/1?start=${start}&end=${end}`)
            const json = await response.json()
            dataset.push(json[query].total_consumption)
        }
        else {
            const response = await fetch(`/apartment_stats/1?start=${start}&end=${end}`)
            const json = await response.json()
            dataset.push(json.total_consumption)
        }
    }
    
    return dataset
}

function getDatasetFromValues(values) {
    return [{
        label: 'Daily consumption in liters',
        data: values,
        backgroundColor: [
            'red',
            'red',
            'red',
            'red',
            'red',
            'red',
            'red',
        ]
    }]
}

async function init() {
    const datasetValues = await getDatasetValues(query)
    const dataset = getDatasetFromValues(datasetValues)
    instantiateChart(dataset)
}

init()